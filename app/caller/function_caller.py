# app/caller/function_caller.py
from typing import Any, Dict, List, Optional
import logging
from app.services.tool_executor import ToolCallExtractor
from app.services.message_preparer import MessagePreparer
from app.utils.message_utils import extract_tool_calls, call_function, function_registry
from app.utils.exceptions import ToolExecutionError

from ..models.AnyModel import AnyModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set the logging level to INFO
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',  # Define the log message format
    datefmt='%Y-%m-%d %H:%M:%S',  # Define the date format
)
logger = logging.getLogger(__name__)

class FunctionCaller:
    def __init__(self, llm: AnyModel, tools: List[Any]):
        """
        Initialize the FunctionCaller with an LLM instance and available tools.

        :param llm: The language model instance to use for processing queries.
        :param tools: A list of tool instances that can be called by the LLM.
        """
        self.llm = llm
        self.tools = tools
        self.message_preparer = MessagePreparer()

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
