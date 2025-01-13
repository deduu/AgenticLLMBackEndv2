# app/managers/qwen_tool_manager.py
import logging
from typing import List, Dict, Any, Tuple
from app.managers.base_tool_manager import BaseToolManager
from app.utils.message_utils import extract_tool_calls, call_function
from app.utils.exceptions import ToolExecutionError
from app.managers.tool_call_extractor import qwen_tool_call_extractor
from app.managers.tool_call_extractor.qwen_tool_call_extractor import QwenToolCallExtractor
import logging
logger = logging.getLogger(__name__)

class QwenToolManager(BaseToolManager):
    def __init__(self):
        self.tool_extractor = QwenToolCallExtractor()
         # Load or initialize anything needed (function registries, etc.)
    async def handle_tool_calls(
        self, 
        initial_response: str,
        messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract tool calls from initial LLM response, execute them, and append results.
        
        Args:
            initial_response (str): The LLM's initial output that may contain tool calls.
            messages (List[Dict[str, Any]]): The conversation messages.

        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: 
                - A list of tool calls for logging or further processing.
                - A list of chart data or any structured output from the tool calls.
        """
        # 1. Extract tool calls
        tool_calls = self.tool_extractor.extract_tool_calls(initial_response)
        logger.info(f"Extracted tool calls: {tool_calls}")

        chart_data = []
        # 2. Execute each tool call
        for idx, tool_call in enumerate(tool_calls):
            try:
                function_name, result = await call_function(tool_call)

                # Record the tool call in messages (for LLM context)
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"type": "function", "function": tool_call}
                    ]
                })

                if not result:
                    error_message = f"Empty result from {function_name}"
                    messages.append({"role": "assistant", "content": error_message})
                    logger.warning(f"Tool Call {idx} Error: {error_message}")
                    continue

                # Example of capturing structured data
                data = {
                    "chartType": result.get("chartType", ""),
                    "data": result.get("data", []),
                    "config": result.get("config", {}),
                    "chartTitle": result.get("chartTitle", "")
                }
                logger.info(f"Tool result: {result}")

                chart_data.append(data)

                # If it's a chart, handle differently
                has_chart = "config" in result
                if not has_chart:
                    messages.append({
                        "role": "ipython", 
                        "name": function_name, 
                        "content": result
                    })
                else:
                    messages.append({
                        "role": "ipython", 
                        "name": function_name, 
                        "content": result.get("rawData", {})
                    })

            except ToolExecutionError as te:
                messages.append({"role": "assistant", "content": str(te)})
                logger.error(f"Tool Call {idx} Error: {str(te)}")
            except Exception as e:
                error_message = f"Unexpected error: {str(e)}"
                messages.append({"role": "assistant", "content": error_message})
                logger.error(f"Tool Call {idx} Unexpected Error: {error_message}")

        return tool_calls, chart_data

