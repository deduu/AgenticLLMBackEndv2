# app/caller/function_caller.py
from typing import Any, Dict, List, Optional
import logging
from app.services.tool_executor import ToolCallExtractor
from app.services.message_preparer import MessagePreparer
from app.handlers.response_handler import ResponseHandler
from app.utils.message_utils import extract_tool_calls, call_function, function_registry
from app.utils.exceptions import ToolExecutionError

# from ..models.llm_interface import LLMInterface
from ..models.parallel_model_pool import ParallelModelPool

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level to INFO
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',  # Define the log message format
    datefmt='%Y-%m-%d %H:%M:%S',  # Define the date format
)
logger = logging.getLogger(__name__)

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
        self.response_handler = ResponseHandler()

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

    # async def process_user_query(
    #     self, 
    #     messages: List[Dict[str, str]], 
    #     tools: List[Any]
    # ) -> str:
    #     """
    #     Process the user query by interacting with the LLM and executing tool calls.

    #     :param messages: The prepared messages to send to the LLM.
    #     :param tools: The list of tools available for execution.
    #     :return: The final response from the LLM.
    #     """
    #     # tool_executor =  ToolCallExtractor(tools=tools)
    #     tool_response = []
    #     chart_data = []

    #     logger.info(f"Message input to LLM: {messages}")
        
    #     # Generate initial response from LLM
    #     try:
    #         initial_response = await self.llm.generate_function_call(messages = messages, tools = function_registry.values())
    #     except Exception as e:
    #         logger.error(f"Error generating initial response: {e}")
    #         raise

    #     logger.info(f"Initial LLM response: {initial_response}")

    #     tool_calls = extract_tool_calls(initial_response)

    #     logger.info(f"Extracted tool calls: {tool_calls}")

    #     for idx, tool_call in enumerate(tool_calls):
    #         try:
    #             function_name, result = await call_function(tool_call)
            

    #             messages.append({
    #                 "role": "assistant", 
    #                 "content": "", 
    #                 "tool_calls": [{"type": "function", "function": tool_call}]
    #             })

    #             if not result:
    #                 error_message = f"Empty result from {function_name}"
    #                 messages.append({"role": "assistant", "content": error_message})
    #                 logger.warning(f"Tool Call {idx} Error: {error_message}")
    #                 continue

    #             data = {
    #                 "chartType": result.get("chartType", ""),
    #                 "data": result.get("data", []),
    #                 "config": result.get("config", {}),
    #                 "chartTitle": result.get("chartTitle", "")
    #             }
    #             logger.info(f"Tool result: {result}")

    #             chart_data.append(data)

    #             has_chart = "config" in result

    #             if not has_chart:
    #                 messages.append({"role": "ipython", "name": function_name, "content": result})
    #             else:
    #                 messages.append({"role": "ipython", "name": function_name, "content": result.get("rawData", {})})

    #         except ToolExecutionError as te:
    #             messages.append({"role": "assistant", "content": str(te)})
    #             logger.error(f"Tool Call {idx} Error: {str(te)}")
    #         except Exception as e:
    #             error_message = f"Unexpected error: {str(e)}"
    #             messages.append({"role": "assistant", "content": error_message})
    #             logger.error(f"Tool Call {idx} Unexpected Error: {error_message}")

    #     logger.info(f"Messages before final response generation: {messages}")

    #     # Handle message transformations
    #     messages = self.response_handler.handle_messages(messages)

    #     # Generate final response from LLM
    #     try:
    #         final_response = await self.llm.generate(messages, max_new_tokens=512)
    #     except Exception as e:
    #         logger.error(f"Error generating final response: {e}")
    #         raise

    #     tool_response.append({
    #         "FunctionName": tool_calls,
    #         "chartData": chart_data,
    #         "Output": final_response.strip().replace('<|eot_id|>', '')
    #     })
    #     logger.info(f"Final tool_response: {tool_response}")

    #     return tool_response
 
