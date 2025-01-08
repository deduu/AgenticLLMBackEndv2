from typing import List, Dict
import json
import datetime
import asyncio
from app.services.tool_executor import ToolCallExtractor
from app.functions.basic_functions import get_current_date
    
def rename_parameters_to_arguments(messages: List[Dict[str, str]], serialize_arguments=False) -> List[Dict[str, str]]:
    """
    Renames 'parameters' to 'arguments' in all tool_calls within the messages list.

    Args:
        messages (list): List of message dictionaries.
        serialize_arguments (bool): If True, converts the 'arguments' value to a JSON string.

    Returns:
        list: The updated list of messages with 'parameters' renamed to 'arguments'.
    """
    for message in messages:
        if 'tool_calls' in message:
            for tool_call in message['tool_calls']:
                function = tool_call.get('function', {})
                if 'parameters' in function:
                    # Rename 'parameters' to 'arguments'
                    function['arguments'] = function.pop('parameters')
                    
                    # Optionally serialize the 'arguments' to a JSON string
                    if serialize_arguments:
                        function['arguments'] = json.dumps(function['arguments'])
    return messages

def convert_dates_to_strings(obj):
    if isinstance(obj, list):
        return [convert_dates_to_strings(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_dates_to_strings(item) for item in obj)
    elif isinstance(obj, dict):
        return {key: convert_dates_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, datetime.date):  # Check if this is datetime.date
        return obj.isoformat()  # Convert to 'YYYY-MM-DD' string
    else:
        return obj

def extract_tool_calls(input_string: str) -> List[Dict[str, str]]:
    # Implement the logic to extract tool calls from the input string
    """
    Wrapper function for backward compatibility.
    """
    extractor = ToolCallExtractor()
    return extractor.extract_tool_calls(input_string)

# Register your functions in a dictionary
function_registry = {
    
    "get_current_date": get_current_date,
    
    # "google_search": google_search
    # "action_price_bitcoin_data": action_price_bitcoin_data
}

async def call_function(function_dict: dict):
    function_name = function_dict.get('function') or function_dict.get('name')
    # Correctly extract arguments without treating empty dict as False
    if 'parameters' in function_dict and function_dict['parameters'] is not None:
        arguments = function_dict['parameters']
    elif 'arguments' in function_dict and function_dict['arguments'] is not None:
        arguments = function_dict['arguments']
    else:
        arguments = {}  #
    
    print(f"Attempting to call function: {function_name}")
    print(f"Arguments: {arguments}")
    
    # Check if the function is in the registry
    if function_name in function_registry:
        func = function_registry[function_name]
        print(f"Retrieved function: {func}")  # Debugging line
        print(f"Function type: {type(func)}")  # Debugging line to confirm it's a function
        
        # Check if it's callable
        if callable(func):
            try:
                # Try to get the function's parameter names
                try:
                     # Get parameter names using the function's __code__ attribute
                    params = func.__code__.co_varnames[:func.__code__.co_argcount]
                    print(f"Parameter names: {params}")
                    # params = inspect.signature(func).parameters
                except AttributeError:
                    print("Failed to get signature using inspect.signature.")
                    # Print the function type for further investigation
                    print(f"Function type on failure: {type(func)}")
                    raise
                
                # Filter arguments to only include those that match the function's parameters
                filtered_args = {k: v for k, v in arguments.items() if k in params}
                print(f"Filtered arguments: {filtered_args}")  # Debugging line
                
                # if inspect.iscoroutinefunction(func):
                if asyncio.iscoroutinefunction(func):
                    return function_name, await func(**filtered_args)
                else:
                    return function_name, func(**filtered_args)
            except Exception as e:
                print(f"Error inspecting or calling function: {e}")
                raise
        else:
            raise ValueError(f"{function_name} is not a callable function")
    else:
        raise ValueError(f"Function {function_name} not found") 
