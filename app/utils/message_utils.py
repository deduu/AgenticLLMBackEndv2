from typing import List, Dict
import json
import datetime
import asyncio
from app.services.tool_executor import ToolCallExtractor
from app.functions.basic_functions import get_current_date
from app.functions.employee_functions import get_query_employee_data
from app.functions.economic_fdi_functions import get_query_economic_data
    
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
    valid_tool_calls = []
    extractor = ToolCallExtractor()
    tool_calls = extractor.extract_tool_calls(input_string)
    print(f"Extracted tool calls now: {json.dumps(tool_calls, indent=2)}")
    for tool_call in tool_calls:
        is_valid, transformed_data, errors = extractor.validate_and_transform_tool_call(tool_call)
        print(f"\nTool Call: {tool_call['name']}")
        print(f"Valid: {is_valid}")
        if transformed_data:
            print(f"Transformed data: {json.dumps(transformed_data, indent=2)}")
            valid_tool_calls.append(transformed_data)
        if errors:
            print("Messages:")
            for error in errors:
                print(f"- {error}")
    print(f"Revised tool calls now: {json.dumps(valid_tool_calls, indent=2)}")
    return valid_tool_calls

# Register your functions in a dictionary
function_registry = {
    
    "get_current_date": get_current_date,
    "get_query_employee_data": get_query_employee_data,
    "get_query_economic_data": get_query_economic_data,
    
    # "google_search": google_search
    # "action_price_bitcoin_data": action_price_bitcoin_data
}
async def call_function(function_dict: dict):
    function_name = function_dict['name']
    raw_parameters = function_dict.get('parameters', {})

    # Normalize arguments structure
    if isinstance(raw_parameters, dict):
        # Extract query_type and parameters intelligently
        query_type = raw_parameters.get('query_type', '')
        inner_parameters = raw_parameters.get('parameters', raw_parameters)
        
        # Ensure a clean structure with query_type and parameters
        arguments = {
            'query_type': query_type,
            'parameters': {k: v for k, v in inner_parameters.items() if k != 'query_type'}
        }
    else:
        arguments = {'parameters': raw_parameters}

    print(f"Attempting to call function: {function_name}")
    print(f"Arguments: {arguments}")

    # Check if the function is in the registry
    if function_name in function_registry:
        func = function_registry[function_name]
        print(f"Retrieved function: {func}")
        print(f"Function type: {type(func)}")
        
        if callable(func):
            try:
                # Get function parameter names
                params = func.__code__.co_varnames[:func.__code__.co_argcount]
                print(f"Parameter names: {params}")

                # Filter arguments to only include those that match the function's parameters
                filtered_args = {k: v for k, v in arguments.items() if k in params}
                print(f"Filtered arguments: {filtered_args}")

                # Call the function
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




# async def call_function(function_dict: dict):
#     # function_name = function_dict['name']
#     # arguments = function_dict['parameters']
#     # function_name = function_dict.get('function') or function_dict.get('name')
#     # Correctly extract arguments without treating empty dict as False
#     # if 'parameters' in function_dict and function_dict['parameters'] is not None:
#     #     arguments = function_dict['parameters']
#     # elif 'arguments' in function_dict and function_dict['arguments'] is not None:
#     #     arguments = function_dict['arguments']
#     # else:
#     #     arguments = {}  #
#     function_name = function_dict['name']
#     raw_parameters= function_dict.get('parameters', {})
    
#     # Normalize arguments structure
#    # Normalize `parameters` to ensure consistency
#     if isinstance(raw_parameters, dict) and 'query_type' in raw_parameters:
#         query_type = raw_parameters.get('query_type', '')
#         arguments = raw_parameters
#     else:
#         query_type = function_dict.get('query_type', '')
#         arguments = {'query_type': query_type, 'parameters': raw_parameters}
    
#     print(f"Attempting to call function: {function_name}")
#     print(f"Arguments: {arguments}")
    
#     # Check if the function is in the registry
#     if function_name in function_registry:
#         func = function_registry[function_name]
#         print(f"Retrieved function: {func}")  # Debugging line
#         print(f"Function type: {type(func)}")  # Debugging line to confirm it's a function
        
#         # Check if it's callable
#         if callable(func):
#             try:
#                 # Try to get the function's parameter names
#                 try:
#                      # Get parameter names using the function's __code__ attribute
#                     params = func.__code__.co_varnames[:func.__code__.co_argcount]
#                     print(f"Parameter names: {params}")
#                     # params = inspect.signature(func).parameters
#                 except AttributeError:
#                     print("Failed to get signature using inspect.signature.")
#                     # Print the function type for further investigation
#                     print(f"Function type on failure: {type(func)}")
#                     raise
                
#                 # Filter arguments to only include those that match the function's parameters
#                 filtered_args = {k: v for k, v in arguments.items() if k in params}
#                 print(f"Filtered arguments: {filtered_args}")  # Debugging line
                
#                 # if inspect.iscoroutinefunction(func):
#                 if asyncio.iscoroutinefunction(func):
#                     return function_name, await func(**filtered_args)
#                 else:
#                     return function_name, func(**filtered_args)
#             except Exception as e:
#                 print(f"Error inspecting or calling function: {e}")
#                 raise
#         else:
#             raise ValueError(f"{function_name} is not a callable function")
#     else:
#         raise ValueError(f"Function {function_name} not found") 
    
    