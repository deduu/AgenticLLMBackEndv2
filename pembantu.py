from app.utils.message_utils import function_registry
# from app.caller.function_caller import FunctionCaller
from app.models.parallel_model_pool import ParallelModelPool
from app.config_loader import load_model_configs
import asyncio


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
        self.models_by_type = {}  #
        
        # Create model instances based on configurations
        for config in model_configs:
            model_type = config.get("model_type")
            if not model_type:
                
                continue
            
            try:
              
                model = ModelFactory.create_model(model_type, config)
                
                model_instance = {
                    "model": model,
                    "device": config["device"]
                }
                self.model_instances.append(model_instance)
                self.queue.put_nowait(model_instance)

                # Store the model by type
                if model_type not in self.models_by_type:
                    self.models_by_type[model_type] = []
                self.models_by_type[model_type].append(model_instance)
                
                # Assign response handler
                self.response_handler[id(model_instance)] = ResponseHandlerFactory.get_response_handler(model_type)

                # Assign tool manager
                self.tool_managers[id(model_instance)] = ToolManagerFactory.get_tool_manager(model_type)
            
            except Exception as e:
                print(f"Failed to load model {config.get('model_path')} of type {model_type}: {e}")
        
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
            print(f"Acquired model on {model_instance['device']}")
            return model_instance
        except asyncio.TimeoutError:
            print("No model instances available and timeout reached.")
            raise HTTPException(
                status_code=503,
                detail="No model instances available. Please try again later."
            )
    
    async def release_model(self, model_instance: Dict[str, Any]):
        """
        Releases a model instance back into the queue.
        """
        await self.queue.put(model_instance)
        print(f"Released model on {model_instance['device']} back to queue")
    
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
                # llamma-specific handling
                return await model.generate_function_call(messages, tools)
            elif isinstance(model, deepSeekLlamaModel):
                # deepseekLlama-specific handling
                return await model.generate_function_call(messages, tools)
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
            elif isinstance(model, deepSeekLlamaModel):
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
            final_response = await self.generate_text(messages, max_new_tokens=512)
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


from typing import Any, Dict, List, Optional


class MessagePreparer:
    def __init__(self, tool_prompt: Optional[str] = None):
        
        self.default_tool_prompt = tool_prompt if tool_prompt else "You are an expert assistant equipped with advanced tool-calling capabilities."

    def prepare_messages(
        self, 
        subquery: str, 
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        tool_calling_prompt = system_prompt if system_prompt else self.default_tool_prompt
        messages = [{"role": "system", "content": tool_calling_prompt}]
        
        if subquery:
            messages.append({"role": "user", "content": subquery})
        
        return messages


class FunctionCaller:
    def __init__(self, llm: ParallelModelPool, tools: List[Any]):
        """
        Initialize the FunctionCaller with an LLM instance and available tools.

        :param llm: The language model instance to use for processing queries.
        :param tools: A list of tool instances that can be called by the LLM.
        """
        self.llm = llm
        self.tools = tools
        self.message_preparer = MessagePreparer()
        # self.tool_executor =  ToolCallExtractor(tools=tools)
        # self.response_handler = ResponseHandler()

    async def execute(
        self, 
        subquery: str, 
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Execute the user query using the LLM and available tools.

        :param subquery: The user's query or subquery.
        :param tools: The list of tools available for the LLM to call.
        :param system_prompt: An optional system prompt to override the default.
        :return: The final response from the LLM after processing.
        """
        messages = self.message_preparer.prepare_messages(subquery, system_prompt)
        # logger.info(f"Messages: {messages}")
        return await self.llm.process_user_query(messages = messages, tools= self.tools)

# Load llm model
config_path = "./config.yaml"
medium_model_configs =  load_model_configs(config_path, "medium")
print(f"Medium model configs: {medium_model_configs}")
model_pool = ParallelModelPool(model_configs=medium_model_configs, num_instances=1)


async def main():
    """
    Main function for the application.

    This function calls the model pool to generate a response based on the provided 
    messages and available tools. Finally, it prints the response.
    """
    function_caller = FunctionCaller(llm = model_pool, tools = function_registry.values())
    # print(f"Messages: {messages}")
    # print(get_current_date)
    # response = await function_caller.execute("what are the trends in FDI in Indonesia across sectors from ASEAN countries between 2010 and 2023?")
    response = await function_caller.execute("which country has the biggest contributor in FDI in Indonesia across sectors from ASEAN countries between 2020 and 2024?")
    print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())  # Run the main function asynchronously