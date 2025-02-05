from typing import Any, Dict, List, Optional
import logging
from dataclasses import dataclass
from enum import Enum
from app.services.tool_executor import ToolCallExtractor
from app.services.message_preparer import MessagePreparer
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
class ToolCallStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    status: ToolCallStatus
    result: Optional[Any] = None
    sub_calls: List['ToolCall'] = None
    parent_call_id: Optional[str] = None

class ToolCallManager:
    """Manages the execution and tracking of tool calls, including nested calls."""
    
    def __init__(self, tools: Dict[str, Any]):
        self.tools = tools
        self.call_history: List[ToolCall] = []
        
    async def execute_tool_call(self, tool_call: ToolCall) -> Any:
        """Execute a single tool call and handle any nested calls."""
        tool_call.status = ToolCallStatus.IN_PROGRESS
        
        try:
            tool = self.tools.get(tool_call.tool_name)
            if not tool:
                raise ValueError(f"Tool {tool_call.tool_name} not found")
            
            result = await tool(**tool_call.arguments)
            tool_call.result = result
            tool_call.status = ToolCallStatus.COMPLETED
            return result
            
        except Exception as e:
            tool_call.status = ToolCallStatus.FAILED
            logger.error(f"Tool call failed: {e}")
            raise

    async def process_nested_calls(self, tool_calls: List[ToolCall]) -> List[Any]:
        """Process a list of tool calls that may contain nested calls."""
        results = []
        for call in tool_calls:
            result = await self.execute_tool_call(call)
            results.append(result)
            
            if call.sub_calls:
                sub_results = await self.process_nested_calls(call.sub_calls)
                results.extend(sub_results)
        
        return results

class ResponseBuilder:
    """Builds final responses by combining tool call results."""
    
    def __init__(self, llm_model):
        self.llm = llm_model
        
    async def build_response(
        self,
        original_query: str,
        tool_results: List[Any],
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Build a coherent response combining the original query and tool results."""
        context_message = self._format_tool_results(tool_results)
        messages = conversation_history + [
            {"role": "system", "content": "Use the following tool results to answer the original query:"},
            {"role": "system", "content": context_message},
            {"role": "user", "content": original_query}
        ]
        
        return await self.llm.generate(messages, max_new_tokens=512)
    
    def _format_tool_results(self, results: List[Any]) -> str:
        """Format tool results into a coherent context message."""
        formatted_results = []
        for idx, result in enumerate(results, 1):
            formatted_results.append(f"Result {idx}: {str(result)}")
        return "\n".join(formatted_results)
    
class EnhancedParallelModelPool(ParallelModelPool):
    """Enhanced version of ParallelModelPool with multi-level tool calling support."""
    
    def __init__(self, model_configs: List[Dict[str, Any]], num_instances: int = 4):
        super().__init__(model_configs, num_instances)
        self.tool_call_manager = None
        self.response_builder = None
    
    def initialize_tools(self, tools: Dict[str, Any]):
        """Initialize tool management components."""
        self.tool_call_manager = ToolCallManager(tools)
        self.response_builder = ResponseBuilder(self)
    
    async def process_user_query(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any],
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """Enhanced query processing with support for nested tool calls."""
        
        # 1. Generate initial response with potential tool calls
        initial_response = await self.generate_function_call(messages, tools)
        logger.info(f"Initial response: {initial_response}")
        
        # 2. Extract and validate tool calls
        tool_calls = await self._extract_tool_calls(initial_response)
        
        # 3. Process tool calls with support for nesting
        results = await self.tool_call_manager.process_nested_calls(
            tool_calls,
            max_depth=max_depth
        )
        
        # 4. Generate final response
        final_response = await self.response_builder.build_response(
            original_query=messages[-1]["content"],
            tool_results=results,
            conversation_history=messages
        )
        
        return {
            "tool_calls": [self._serialize_tool_call(call) for call in tool_calls],
            "results": results,
            "final_response": final_response
        }
    
    async def _extract_tool_calls(self, response: str) -> List[ToolCall]:
        """Extract tool calls from the LLM response."""
        # Implementation depends on your specific response format
        # This is a placeholder for the actual implementation
        pass
    
    def _serialize_tool_call(self, tool_call: ToolCall) -> Dict[str, Any]:
        """Convert a ToolCall object to a serializable dictionary."""
        return {
            "tool_name": tool_call.tool_name,
            "arguments": tool_call.arguments,
            "status": tool_call.status.value,
            "result": tool_call.result,
            "sub_calls": [
                self._serialize_tool_call(sub_call) 
                for sub_call in (tool_call.sub_calls or [])
            ]
        }

class Asisten:
    """Enhanced version of FunctionCaller with support for multi-level tool calling."""
    
    def __init__(
        self,
        llm: EnhancedParallelModelPool,
        tools: Dict[str, Any],
        max_depth: int = 3
    ):
        self.llm = llm
        self.llm.initialize_tools(tools)
        self.tools = tools
        self.max_depth = max_depth
        self.message_preparer = MessagePreparer()
    
    async def execute(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Execute the user query with support for nested tool calls.
        
        Args:
            query: The user's query
            system_prompt: Optional system prompt
            conversation_history: Optional conversation history
            
        Returns:
            Dict containing tool calls, results, and final response
        """
        messages = self.message_preparer.prepare_messages(query, system_prompt)
        if conversation_history:
            messages = conversation_history + messages
            
        return await self.llm.process_user_query(
            messages=messages,
            tools=list(self.tools.values()),
            max_depth=self.max_depth
        )
