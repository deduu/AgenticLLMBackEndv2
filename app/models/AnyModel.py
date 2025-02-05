# app/models/parallel_model_pool.py
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any, Tuple

import torch
from fastapi import HTTPException

from app.utils.system_prompt import agentic_prompt
from app.handlers.context_handler import ContextPreparer
from app.services.message_preparer import MessagePreparer

from .llamma_model import llammaModel
from .qwen_model import QwenModel
from .deepseek_model import deepSeekLlamaModel

from ..models.model_factory import ModelFactory
from ..managers.tool_manager_factory import ToolManagerFactory
from ..managers.base_tool_manager import BaseToolManager
from app.handlers.response.response_handler_factory import ResponseHandlerFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level to INFO
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",  # Define the log message format
    datefmt="%Y-%m-%d %H:%M:%S",  # Define the date format
)
logger = logging.getLogger(__name__)


class AnyModel():
    """
    Manages a pool of model instances for parallel inference across multiple CUDA devices.
    Utilizes an asyncio.Queue to handle request queuing when all models are busy.
    Supports multiple model types via a factory pattern.
    """

    def __init__(self, model_configs: List[Dict[str, Any]], num_instances: int = 4):
        """
        Initializes the model pool with multiple model configurations.

        Args:
            model_configs (List[Dict[str, Any]]): List of model configurations. Each config should include
                'model_type', 'model_path', 'device', and any other required parameters.
            num_instances (int): Total number of model instances to load across all model types.
        """
        self.queue = asyncio.Queue(maxsize=num_instances)
        self.model_instances: List[Dict[str, Any]] = []
        self.tool_managers: Dict[int, BaseToolManager] = {}
        self.response_handler: Dict[int, Any] = {}
        self.models_by_type: Dict[str, List[Dict[str, Any]]] = {}

        for config in model_configs:
            model_type = config.get("model_type")
            if not model_type:
                logger.error("Model configuration missing 'model_type'")
                continue

            try:
                logger.info(f"Creating model of type: {model_type}")
                model = ModelFactory.create_model(model_type, config)
                model_instance = {"model": model, "device": config["device"]}
                self.model_instances.append(model_instance)
                self.queue.put_nowait(model_instance)

                # Organize models by type
                self.models_by_type.setdefault(model_type, []).append(model_instance)

                # Assign response handler and tool manager for the model instance
                instance_id = id(model_instance)
                self.response_handler[instance_id] = ResponseHandlerFactory.get_response_handler(model_type)
                self.tool_managers[instance_id] = ToolManagerFactory.get_tool_manager(model_type)

                logger.info(f"Loaded and enqueued {config.get('model_path')} model on {config['device']}")
            except Exception as e:
                logger.exception(f"Failed to load model {config.get('model_path')} of type {model_type}: {e}")

    @property
    def device(self) -> str:
        return "pool"

    async def get_model_by_type(self, model_type: str) -> Dict[str, Any]:
        """
        Retrieve a specific model instance by type.
        """
        if self.models_by_type.get(model_type):
            return self.models_by_type[model_type][0]
        raise ValueError(f"No available model of type: {model_type}")

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

    @asynccontextmanager
    async def acquire_model(self, timeout: Optional[float] = None):
        """
        Async context manager to acquire and release a model instance.
        """
        model_instance = await self.get_free_model(timeout)
        try:
            yield model_instance
        finally:
            await self.release_model(model_instance)

    async def generate_function_call(
        self, messages: List[Dict[str, str]], tools: List[Any]
    ) -> str:
        """
        Generate an LLM response that may include function calls.
        """
        async with self.acquire_model(timeout=30) as model_instance:
            model = model_instance["model"]
            # All supported models are assumed to have the generate_function_call interface.
            if hasattr(model, "generate_function_call"):
                return await model.generate_function_call(messages, tools)
            raise ValueError("Unsupported model type for function call generation")

    async def generate_text_stream(
        self,
        query: str,
        context: Any,
        history_messages: Optional[List[Dict]] = None,
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        timeout: Optional[float] = None,
    ):
        """
        Stream-generated text from the model in chunks (SSE or similar).
        """
        async with self.acquire_model(timeout=timeout) as model_instance:
            model = model_instance["model"]
            if isinstance(model, QwenModel):
                async for chunk in model.generate_text_stream(
                    query=query,
                    context=context,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                ):
                    yield chunk
            elif isinstance(model, (llammaModel, deepSeekLlamaModel)):
                async for chunk in model.generate_text_stream(
                    query=query,
                    context=context,
                    history_messages=history_messages,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                ):
                    yield chunk
            else:
                raise ValueError("Unsupported model type for text streaming")

    async def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 128) -> str:
        """
        Generate a standard text response (non-streaming).
        """
        async with self.acquire_model(timeout=30) as model_instance:
            model = model_instance["model"]
            if hasattr(model, "generate_text"):
                return await model.generate_text(messages, max_new_tokens)
            raise ValueError("Unsupported model type for text generation")

    async def handle_tool_calls(
        self, initial_response: str, messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Handle tool calls extracted from the initial LLM response using the appropriate ToolManager.

        Returns:
            Tuple containing a list of tool calls and a list of chart data or other outputs.
        """
        async with self.acquire_model(timeout=30) as model_instance:
            instance_id = id(model_instance)
            tool_manager = self.tool_managers.get(instance_id)
            if not tool_manager:
                raise ValueError("No ToolManager assigned to this model instance")
            return await tool_manager.handle_tool_calls(initial_response, messages)

    async def handle_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        1. Generate an initial response that may contain tool calls.
        2. Execute those tool calls.
        3. Optionally generate a final response combining all results.
        4. Return the full tool response.
        """
        async with self.acquire_model(timeout=30) as model_instance:
            instance_id = id(model_instance)
            response_handler = self.response_handler.get(instance_id)
            if not response_handler:
                raise ValueError("No ResponseHandler assigned to this model instance")
            return await response_handler.handle_messages(messages)

    async def process_user_query(self, messages: List[Dict[str, str]], tools: List[Any]) -> str:
        """
        Process a user query by:
            1. Generating an initial response (potentially with tool calls)
            2. Handling tool calls
            3. Transforming messages
            4. Generating a final response that combines results.
        """
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

        # 3. Transform messages before final generation
        try:
            messages = await self.handle_messages(messages)
            logger.info(f"Messages after transformation: {messages}")
        except Exception as e:
            logger.error(f"Error handling messages: {e}")
            raise

        # 4. Generate final response after tool calls
        try:
            final_response = await self.generate(messages, max_new_tokens=512)
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            raise

        # Assemble results
        tool_response = [{
            "FunctionName": tool_calls,
            "chartData": chart_data,
            "Output": final_response.strip().replace("<|eot_id|>", "")
        }]
        logger.info(f"Final tool_response: {tool_response}")

        return tool_response
