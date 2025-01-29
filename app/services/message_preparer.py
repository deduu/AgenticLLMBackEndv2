from typing import List, Dict, Optional
from collections import defaultdict, deque
from typing import Dict, List, Any

from ..utils.system_prompt import tool_prompt, user_prompt_template
# from ..prompt.user_prompt_template import user_prompt_template

from ..functions.function_definition_list import function_definitions_json

from ..utils.tracker import log_partial_message


class DependencyError(Exception):
    """Base class for dependency-related errors."""
    pass

class CycleError(DependencyError):
    """Raised when a cycle is detected in dependencies."""
    def __init__(self, cycle_nodes: List[str]):
        message = f"Cycle detected in subquery dependencies: {' -> '.join(cycle_nodes)}"
        super().__init__(message)
        self.cycle_nodes = cycle_nodes

class UndefinedDependencyError(DependencyError):
    """Raised when a subquery depends on an undefined subquery."""
    def __init__(self, subquery_id: str, undefined_dep: str):
        message = f"Subquery '{subquery_id}' depends on undefined subquery '{undefined_dep}'."
        super().__init__(message)
        self.subquery_id = subquery_id
        self.undefined_dep = undefined_dep

class MessagePreparer:
    def __init__(self, tool_prompt: str = tool_prompt):
        self.default_tool_prompt = tool_prompt

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
    
    def prepare_query_for_message(self, query: str, system_prompt: Optional[str] = None, history_messages: Optional[str] = None) -> List[Dict[str, str]]:
        
        system_prompt_default = (
            "You are an intelligent assistant tasked with refining subqueries based on their dependencies, ensuring clarity and precision.\n\n"
        )
        system_message = system_prompt if system_prompt else system_prompt_default
        history_messages = history_messages if history_messages else ""

        user_message = user_prompt_template.substitute(
            history=history_messages,
            user_query=query,
            functions=function_definitions_json,
        )
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]
        log_partial_message(f"messages: {messages}")
        return messages
    
    def prepare_query_for_summary(self, query: str, system_prompt: Optional[str] = None, history_messages: Optional[str] = None) -> List[Dict[str, str]]:
        
        system_prompt_default = (
            "You are an intelligent assistant tasked with refining subqueries based on their dependencies, ensuring clarity and precision.\n\n"
        )
        system_message = system_prompt if system_prompt else system_prompt_default
        history_messages = history_messages if history_messages else ""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": history_messages},
        ]
        log_partial_message(f"messages: {messages}")
        return messages

    def determine_processing_order(self, subqueries):
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        for subquery_id, data in subqueries.items():
            depends_on = data.get("DependsOn", [])
            for dep in depends_on:
                graph[dep].append(subquery_id)
                in_degree[subquery_id] += 1
            if subquery_id not in in_degree:
                in_degree[subquery_id] = in_degree.get(subquery_id, 0)

        # Kahn's algorithm for topological sorting
        queue = deque([node for node in in_degree if in_degree[node] == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(subqueries):
            raise Exception("Cycle detected in subquery dependencies")

        return order


    def construct_dependency_info(self, combined_response: Dict[str, Any], dependencies: Dict[str, Any]) -> str:
            """
            Constructs a dependency information string from combined responses.

            Args:
                combined_response (Dict[str, Any]): The dictionary containing subquery results.
                dependencies (Dict[str, Any]): The dictionary containing the current subquery depends on.

            Returns:
                str: Formatted dependency information.
            """
            dependency_info = ""
            for dep_id, dep_data in dependencies.items():
                # Retrieve the corresponding data from combined_response
                dep_data = combined_response.get(dep_id)
                if not dep_data:
                    continue  # Skip if dependency data is missing

                dep_type = dep_data.get('Type')

                if dep_type == 'RAG':
                    sources = dep_data.get('Source', [])
                    
                    # Check if 'Source' is a list of dictionaries
                    if isinstance(sources, list):
                        # Iterate over the list of sources
                        for source in sources:
                            text = source.get('text', '')
                            dependency_info += f"{dep_id} Result: {text}\n"
                    else:
                        # Handle unexpected case where Source is not a list
                        dependency_info += f"{dep_id} has no valid sources.\n"

                elif dep_type == 'Action':
                    # Handle Action type
                    sources = dep_data.get('Source', [])
                    
                    # Check if 'Source' is a list and iterate
                    if isinstance(sources, list):
                        for source in sources:
                            output = source.get('Output', '')
                            dependency_info += f"{dep_id} Result: {output}\n"
                    else:
                        # Handle unexpected case where Source is not a list
                        dependency_info += f"{dep_id} has no valid action sources.\n"

            return dependency_info.strip().replace('<|eot_id|>', '')
