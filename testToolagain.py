from typing import Any, Dict, List, Optional, Tuple
from logging import getLogger
from fastapi import HTTPException
import asyncio
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

logger = getLogger(__name__)

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
    priority: int = 0  # Lower number = higher priority
    dependencies: List[str] = None  # List of tool names this call depends on
    result: Optional[Any] = None

class ParallelToolExecutor:
    """Executes multiple tool calls in parallel while respecting dependencies."""
    
    def __init__(self, tools: Dict[str, Any], max_concurrent: int = 5):
        self.tools = tools
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_tool(self, tool_call: ToolCall) -> Any:
        """Execute a single tool call with semaphore control."""
        async with self.semaphore:
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

    async def execute_parallel(self, tool_calls: List[ToolCall]) -> Dict[str, Any]:
        """Execute tool calls in parallel while respecting dependencies."""
        
        # Group tools by priority level
        priority_groups = defaultdict(list)
        for call in tool_calls:
            priority_groups[call.priority].append(call)
        
        results = {}
        # Execute tools in priority order
        for priority in sorted(priority_groups.keys()):
            group = priority_groups[priority]
            
            # Filter tools that have their dependencies met
            executable_calls = [
                call for call in group
                if not call.dependencies or 
                all(dep in results for dep in call.dependencies)
            ]
            
            # Execute current group in parallel
            tasks = []
            for call in executable_calls:
                if call.dependencies:
                    # Update arguments with dependency results
                    for dep in call.dependencies:
                        call.arguments[f"{dep}_result"] = results[dep]
                
                tasks.append(self.execute_tool(call))
            
            if tasks:
                group_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Store results
                for call, result in zip(executable_calls, group_results):
                    if isinstance(result, Exception):
                        logger.error(f"Tool {call.tool_name} failed: {result}")
                        continue
                    results[call.tool_name] = result
        
        return results

class EnhancedParallelModelPool(ParallelModelPool):
    """Enhanced version of ParallelModelPool with parallel tool execution."""
    
    def __init__(self, model_configs: List[Dict[str, Any]], num_instances: int = 4):
        super().__init__(model_configs, num_instances)
        self.tool_executor = None
        self.response_builder = None
    
    def initialize_tools(self, tools: Dict[str, Any], max_concurrent: int = 5):
        """Initialize tool execution components."""
        self.tool_executor = ParallelToolExecutor(tools, max_concurrent)
        self.response_builder = ResponseBuilder(self)
    
    async def process_user_query(
        self,
        messages: List[Dict[str, str]],
        tools: List[Any],
    ) -> Dict[str, Any]:
        """Process query with parallel tool execution."""
        
        # 1. Generate initial response with potential tool calls
        initial_response = await self.generate_function_call(messages, tools)
        logger.info(f"Initial response: {initial_response}")
        
        # 2. Extract and structure tool calls with dependencies
        tool_calls = await self._extract_tool_calls(initial_response)
        
        # 3. Execute tools in parallel
        results = await self.tool_executor.execute_parallel(tool_calls)
        
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

class EnhancedFunctionCaller:
    """Function caller with parallel tool execution support."""
    
    def __init__(
        self,
        llm: EnhancedParallelModelPool,
        tools: Dict[str, Any],
        max_concurrent: int = 5
    ):
        self.llm = llm
        self.llm.initialize_tools(tools, max_concurrent)
        self.tools = tools
        self.message_preparer = MessagePreparer()
    
    async def execute(
        self,
        query: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Execute the user query with parallel tool execution."""
        messages = self.message_preparer.prepare_messages(query, system_prompt)
        if conversation_history:
            messages = conversation_history + messages
            
        return await self.llm.process_user_query(
            messages=messages,
            tools=list(self.tools.values())
        )

from app.models.parallel_model_pool import ParallelModelPool
from app.config_loader import load_model_configs
config_path = "./config.yaml"
medium_model_configs =  load_model_configs(config_path, "medium")
print(f"Medium model configs: {medium_model_configs}")

# Example usage showing parallel execution of tools
async def main():
    # Initialize the model pool
    model_pool = EnhancedParallelModelPool(
        model_configs=medium_model_configs,
        num_instances=1
    )
    
    # Create function caller with parallel execution support
    function_caller = EnhancedFunctionCaller(
        llm=model_pool,
        tools=function_registry,
        max_concurrent=5  # Maximum number of concurrent tool executions
    )
    
    # Execute a query that will trigger multiple tool calls
    response = await function_caller.execute(
        "Analyze FDI trends in Indonesia, including sector-wise breakdown and "
        "comparison with historical data. Also provide economic impact assessment."
    )
    
    print("Results:", response["results"])
    print("Final response:", response["final_response"])

if __name__ == "__main__":
    asyncio.run(main())