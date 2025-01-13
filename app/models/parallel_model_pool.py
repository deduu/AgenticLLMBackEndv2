# app/models/parallel_model_pool.py
import asyncio
import torch
import logging
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException

from app.utils.system_prompt import agentic_prompt
from app.handlers.context_handler import ContextPreparer
from app.services.message_preparer import MessagePreparer
from app.handlers.response_handler import ResponseHandler

from .llamma_model import llammaModel
from .qwen_model import QwenModel

# from app.managers.generation_manager import GenerationManager
# from app.managers.tool_manager import ToolManager
from ..models.model_factory import ModelFactory
from ..managers.tool_manager_factory import ToolManagerFactory
from ..managers.base_tool_manager import BaseToolManager
from ..handlers.response_handler_factory import ResponseHandlerFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level to INFO
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',  # Define the log message format
    datefmt='%Y-%m-%d %H:%M:%S',  # Define the date format
)
logger = logging.getLogger(__name__)

class ParallelModelPool():
    """
    Manages a pool of model instances for parallel inference across multiple CUDA devices.
    Utilizes an asyncio.Queue to handle request queuing when all models are busy.
    Supports multiple model types via a factory pattern.
    """
    def __init__(
        self,
        model_configs: List[Dict[str, Any]],
        num_instances: int = 4,
    ):
        """
        Initializes the model pool with multiple model configurations.
        
        Args:
            model_configs (List[Dict[str, Any]]): List of model configurations. Each config should include 'model_type', 'model_path', 'device', and any other required parameters.
            num_instances (int): Total number of model instances to load across all model types.
        """
        
        # Create a queue to manage free (available) model instances
        self.queue = asyncio.Queue(maxsize=num_instances)
        self.model_instances = []
        self.tool_managers = {}
        self.response_handler = {}
        
        # Create model instances based on configurations
        for config in model_configs:
            model_type = config.get("model_type")
            if not model_type:
                logger.error("Model configuration missing 'model_type'")
                continue
            
            try:
                model = ModelFactory.create_model(model_type, config)
                model_instance = {
                    "model": model,
                    "device": config["device"]
                }
                self.model_instances.append(model_instance)
                self.queue.put_nowait(model_instance)
                
                # Assign response handler
                self.response_handler[id(model_instance)] = ResponseHandlerFactory.get_response_handler(model_type)

                # Assign tool manager
                self.tool_managers[id(model_instance)] = ToolManagerFactory.get_tool_manager(model_type)
                logger.info(f"model: {self.tool_managers[id(model_instance)]}")
                logger.info(f"Loaded and enqueued {config.get('model_path')} model on {config['device']}")
            except Exception as e:
                logger.error(f"Failed to load model {config.get('model_path')} of type {model_type}: {e}")
        
        # Initialize the generation and tool managers if needed
        # Depending on whether they are model-specific or not

    @property
    def device(self):
        return "pool"
    
    async def get_free_model(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Acquire a free model instance from the queue within the given timeout.
        Raises HTTPException if no model becomes available.
        """
        try:
            model_instance = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            logger.debug(f"Acquired model on {model_instance['device']}")
            return model_instance
        except asyncio.TimeoutError:
            logger.warning("No model instances available and timeout reached.")
            raise HTTPException(
                status_code=503,
                detail="No model instances available. Please try again later."
            )
    
    async def release_model(self, model_instance: Dict[str, Any]):
        """
        Releases a model instance back into the queue.
        """
        await self.queue.put(model_instance)
        logger.debug(f"Released model on {model_instance['device']} back to queue")
    
    async def generate_function_call(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any]
    ) -> str:
        """
        Generate an LLM response that may include function calls.
        """
        model_instance = await self.get_free_model(timeout=30)
        try:
            model = model_instance["model"]
            if isinstance(model, QwenModel):
                # Qwen-specific handling
                return await model.generate_function_call(messages, tools)
            elif isinstance(model, llammaModel):
                # Gemini-specific handling
                return await model.generate_function_call(messages, tools)
            else:
                raise ValueError("Unsupported model type")
        finally:
            await self.release_model(model_instance)
    
    async def generate_text_stream(
        self,
        query: str,
        context: Any,
        history_messages: Optional[List[Dict]] = None,
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: Optional[float] = None
    ):
        """
        Stream-generated text from the model in chunks (SSE or similar).
        """
        model_instance = await self.get_free_model(timeout=timeout)
        try:
            model = model_instance["model"]
            if isinstance(model, QwenModel):
                # Qwen-specific streaming
                async for chunk in model.generate_text_stream(
                    query=query,
                    context=context,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p
                ):
                    yield chunk
            elif isinstance(model, llammaModel):
                # Gemini-specific streaming
                async for chunk in model.generate_text_stream(
                    query=query,
                    context=context,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p
                ):
                    yield chunk
            else:
                raise ValueError("Unsupported model type")
        finally:
            await self.release_model(model_instance)
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 128
    ) -> str:
        """
        Generate a standard text response (non-streaming).
        """
        model_instance = await self.get_free_model(timeout=30)
        try:
            model = model_instance["model"]
            if isinstance(model, QwenModel):
                return await model.generate_text(messages, max_new_tokens)
            elif isinstance(model, llammaModel):
                return await model.generate_text(messages, max_new_tokens)
            else:
                raise ValueError("Unsupported model type")
        finally:
            await self.release_model(model_instance)
    
    async def handle_tool_calls(
        self, 
        initial_response: str,
        messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Handle tool calls extracted from the initial LLM response using the appropriate ToolManager.
        
        Args:
            initial_response (str): The initial response from the LLM that may contain tool calls.
            messages (List[Dict[str, Any]]): The conversation messages.
        
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: 
                - List of tool calls.
                - List of chart data or other structured outputs.
        """
        model_instance = await self.get_free_model(timeout=30)
        try:
            logger.info(f"model_instance: {model_instance}")
            tool_manager = self.tool_managers.get(id(model_instance))
            logger.info(f"tool_manager: {tool_manager}")
            if not tool_manager:
                raise ValueError("No ToolManager assigned to this model instance")
            return await tool_manager.handle_tool_calls(initial_response, messages)
        finally:
            await self.release_model(model_instance)
    
    async def handle_messages(
        self,
        messages: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        1. Generate an initial response that may contain tool calls.
        2. Execute those tool calls.
        3. Optionally generate a final response combining all results.
        4. Return the full tool response (function calls, chart data, final output, etc.).
        """
        model_instance = await self.get_free_model(timeout=30)
        try:
            response_handler = self.response_handler.get(id(model_instance))
            if not response_handler:
                raise ValueError("No ResponseHandler assigned to this model instance")
            return await response_handler.handle_messages(messages)
        finally:      
            await self.release_model(model_instance)

    async def process_user_query(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any]
    ) -> str:
        """
        1. Generate an initial response that may contain tool calls.
        2. Execute those tool calls.
        3. Optionally generate a final response combining all results.
        4. Return the full tool response (function calls, chart data, final output, etc.).
        """
        tool_response = []
        chart_data = []     
    
        # 1. Generate initial response (potentially containing tool calls)
        try:
            initial_response = await self.generate_function_call(messages, tools)
            logger.info(f"Initial LLM response: {initial_response}")
        except Exception as e:
            logger.error(f"Error generating initial response: {e}")
            raise
    
        # 2. Handle tool calls
        try:
            tool_calls, chart_data = await self.handle_tool_calls(initial_response, messages)
            logger.info(f"Tool calls: {tool_calls}")
        except Exception as e:
            logger.error(f"Error handling tool calls: {e}")
            raise
            
    
        # 3. transform messages before final generation
        try:
            messages = await self.handle_messages(messages)
            logger.info(f"Messages after message transformation: {messages}")
        except Exception as e:
            logger.error(f"Error handling messages: {e}")
            raise
    
        # 4. Generate final response after tool calls
        try:
            final_response = await self.generate(messages, max_new_tokens=512)
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            raise
    
        # 4. Assemble results
        tool_response.append({
            "FunctionName": tool_calls,
            "chartData": chart_data,
            "Output": final_response.strip().replace('<|eot_id|>', '')
        })
        logger.info(f"Final tool_response: {tool_response}")
    
        return tool_response
