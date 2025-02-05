import asyncio
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from app.utils.tracker import log_processing_time

# Setup a simple logger.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The provided definitions
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
    
# Define a simple asynchronous tool.
async def echo_tool(message: str) -> str:
    await asyncio.sleep(0.5)  # Simulate some delay
    return f"Echo: {message}"

async def test_single_tool_call():
    # Setup the tool dictionary.
    tools = {"echo": echo_tool}
    manager = ToolCallManager(tools)
    
    # Create a ToolCall object.
    call = ToolCall(
        tool_name="echo",
        arguments={"message": "Hello, world!"},
        status=ToolCallStatus.PENDING
    )
    
    result = await manager.execute_tool_call(call)
    print("Result:", result)
    print("Call Status:", call.status)

# Define two asynchronous tools.
async def add_tool(a: int, b: int) -> int:
    await asyncio.sleep(0.5)
    return a + b

async def multiply_tool(a: int, b: int) -> int:
    await asyncio.sleep(0.5)
    return a * b

@log_processing_time
async def test_nested_tool_calls():
    tools = {
        "add": add_tool,
        "multiply": multiply_tool
    }
    manager = ToolCallManager(tools)
    
    # Main tool call that uses the add tool
    main_call = ToolCall(
        tool_name="add",
        arguments={"a": 5, "b": 3},
        status=ToolCallStatus.PENDING,
        sub_calls=[
            # Nested tool call that uses the multiply tool
            ToolCall(
                tool_name="multiply",
                arguments={"a": 2, "b": 4},
                status=ToolCallStatus.PENDING
            )
        ]
    )
    
    results = await manager.process_nested_calls([main_call])
    print("Results:", results)
    print("Main Call Status:", main_call.status)
    if main_call.sub_calls:
        for sub_call in main_call.sub_calls:
            print("Sub Call Status:", sub_call.status)
    
# Run the test:
asyncio.run(test_nested_tool_calls())



