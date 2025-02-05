import re
import json
import inspect
import ast
import difflib
from typing import Any, Dict, Optional, Tuple, Union, List
from dataclasses import dataclass
from enum import Enum
import datetime
from app.services.schema_transformer import SchemaTransformer

# class SchemaTransformer:
#     def __init__(self):
#         self.transformations = []
        
#     @dataclass
#     class Transformation:
#         from_path: str
#         to_path: str
#         old_value: Any
#         new_value: Any
        
#     def find_closest_match(self, value: str, valid_values: list[str]) -> str:
#         if not valid_values:
#             return value
#         return difflib.get_close_matches(value, valid_values, n=1, cutoff=0.6)[0] if difflib.get_close_matches(value, valid_values, n=1, cutoff=0.6) else value

#     def extract_valid_values_from_docstring(self, docstring: str, field_name: str) -> list[str]:
#         try:
#             field_start = docstring.find(f"{field_name}:")
#             if field_start == -1:
#                 return []
            
#             values_start = docstring.find("(", field_start)
#             if values_start == -1:
#                 values_start = docstring.find(":", field_start)
#             if values_start == -1:
#                 return []
                
#             values_end = docstring.find(")", values_start)
#             if values_end == -1:
#                 values_end = docstring.find("\n", values_start)
#             if values_end == -1:
#                 return []
                
#             values_str = docstring[values_start + 1:values_end]
#             return [v.strip() for v in values_str.split(",")]
#         except:
#             return []

#     def transform_value(self, value: Any, expected_type: str) -> Any:
#         try:
#             if expected_type == "string":
#                 return str(value)
#             elif expected_type == "integer":
#                 return int(float(value))
#             elif expected_type == "float":
#                 return float(value)
#             elif expected_type == "boolean":
#                 if isinstance(value, str):
#                     return value.lower() in ("true", "1", "yes")
#                 return bool(value)
#             elif expected_type == "list":
#                 if isinstance(value, str):
#                     try:
#                         return ast.literal_eval(value)
#                     except:
#                         return [value]
#                 elif isinstance(value, list):
#                     return value
#                 else:
#                     return [value]
#             elif expected_type == "dict":
#                 if isinstance(value, str):
#                     try:
#                         return json.loads(value)
#                     except:
#                         return {"value": value}
#                 elif isinstance(value, dict):
#                     return value
#                 else:
#                     return {"value": value}
#             return value
#         except:
#             return value

#     def find_value_in_nested_dict(self, data: Dict, key: str) -> Tuple[Any, str]:
#         def _search(d: Dict, path: str = "") -> Tuple[Any, str]:
#             if not isinstance(d, dict):
#                 return None, ""
                
#             for k, v in d.items():
#                 current_path = f"{path}.{k}" if path else k
#                 if k == key:
#                     return v, current_path
#                 elif isinstance(v, dict):
#                     found_value, found_path = _search(v, current_path)
#                     if found_value is not None:
#                         return found_value, found_path
#             return None, ""
            
#         return _search(data)

#     def transform_data(self, data: Dict, schema: Dict, docstring: str, current_path: str = "") -> Dict:
#         result = {}
        
#         for key, expected in schema.items():
#             new_path = f"{current_path}.{key}" if current_path else key
            
#             value, value_path = self.find_value_in_nested_dict(data, key)
            
#             if value is None and key in data:
#                 value = data[key]
#                 value_path = new_path
            
#             if isinstance(expected, dict):
#                 if value is None:
#                     value = {}
#                 if not isinstance(value, dict):
#                     value = {"value": value}
#                 result[key] = self.transform_data(value, expected, docstring, new_path)
#             else:
#                 if value is not None:
#                     transformed_value = self.transform_value(value, expected)
                    
#                     if expected == "string":
#                         valid_values = self.extract_valid_values_from_docstring(docstring, key)
#                         if valid_values:
#                             transformed_value = self.find_closest_match(str(transformed_value), valid_values)
                    
#                     if transformed_value != value:
#                         self.transformations.append(self.Transformation(
#                             from_path=value_path or new_path,
#                             to_path=new_path,
#                             old_value=value,
#                             new_value=transformed_value
#                         ))
#                     result[key] = transformed_value
#                 else:
#                     default_value = self.get_default_value(expected)
#                     result[key] = default_value
#                     self.transformations.append(self.Transformation(
#                         from_path=new_path,
#                         to_path=new_path,
#                         old_value=None,
#                         new_value=default_value
#                     ))
        
#         return result

#     def get_default_value(self, type_str: str) -> Any:
#         defaults = {
#             "string": "",
#             "integer": 0,
#             "float": 0.0,
#             "boolean": False,
#             "list": [],
#             "dict": {}
#         }
#         return defaults.get(type_str, None)

#     def transform_to_valid_input(self, function, input_data: Union[str, Dict]) -> Tuple[Dict, list[Transformation]]:
#         self.transformations = []
        
#         try:
#             if isinstance(input_data, str):
#                 data = json.loads(input_data)
#             else:
#                 data = input_data
                
#             docstring = inspect.getdoc(function)
#             if not docstring:
#                 raise ValueError("Function must have a docstring")
                
#             schema_start = docstring.find("Input format:")
#             if schema_start == -1:
#                 schema_start = docstring.find("```")
#             if schema_start == -1:
#                 raise ValueError("Could not find schema definition in docstring")
                
#             schema_text = docstring[schema_start:]
#             start_brace = schema_text.find("{")
#             end_brace = schema_text.rfind("}")
            
#             if start_brace == -1 or end_brace == -1:
#                 raise ValueError("Could not find JSON structure in docstring")
                
#             schema_json = schema_text[start_brace:end_brace + 1]
            
#             schema_json = schema_json.replace("str,", '"string",')
#             schema_json = schema_json.replace("int,", '"integer",')
#             schema_json = schema_json.replace("float,", '"float",')
#             schema_json = schema_json.replace("bool,", '"boolean",')
#             schema_json = schema_json.replace("list,", '"list",')
#             schema_json = schema_json.replace("dict,", '"dict",')
            
#             schema = json.loads(schema_json)
            
#             transformed_data = self.transform_data(data, schema, docstring)
            
#             return transformed_data, self.transformations
            
#         except Exception as e:
#             raise ValueError(f"Transformation error: {str(e)}")

class ToolCallExtractor:
    def __init__(self):
        self.complete_pattern = re.compile(r'<\|python_tag\|>(.*?)<\|eom_id\|>', re.DOTALL)
        self.partial_pattern = re.compile(r'(.*?)<\|(?:eom_id|eot_id)\|>', re.DOTALL)
        self.transformer = SchemaTransformer()
        self.function_registry = {}

    def register_function(self, name: str, function):
        """Register a function with its schema for validation."""
        self.function_registry[name] = function

    def _clean_and_parse_json(self, json_str):
        try:
            json_str = json_str.strip()
            if json_str.startswith('{'):
                return json.loads(json_str)
            return None
        except json.JSONDecodeError:
            return None

    def _extract_json_objects(self, text):
        json_objects = []
        decoder = json.JSONDecoder()
        pos = 0
        text_length = len(text)
        while pos < text_length:
            while pos < text_length and text[pos].isspace():
                pos += 1
            if pos >= text_length:
                break
            try:
                obj, end = decoder.raw_decode(text, pos)
                json_objects.append(obj)
                pos = end
            except json.JSONDecodeError:
                pos += 1
        return json_objects

    def extract_tool_calls(self, input_string):
        tool_calls = []
        
        complete_matches = self.complete_pattern.findall(input_string)
        if complete_matches:
            for match in complete_matches:
                tool_calls.extend(self._extract_json_objects(match))
            return tool_calls
            
        partial_matches = self.partial_pattern.findall(input_string)
        if partial_matches:
            for match in partial_matches:
                tool_calls.extend(self._extract_json_objects(match))
            return tool_calls
            
        tool_calls.extend(self._extract_json_objects(input_string))
        
        return tool_calls

    def validate_and_transform_tool_call(self, tool_call: Dict) -> Tuple[bool, Optional[Dict], List[str]]:
        """
        Validate and transform a tool call against its registered schema.
        Returns (is_valid, transformed_data, error_messages).
        """
        errors = []
        
        if not isinstance(tool_call, dict):
            errors.append("Tool call must be a dictionary")
            return False, None, errors
            
        if 'name' not in tool_call:
            errors.append("Tool call must have a 'name' field")
            return False, None, errors
            
        if not isinstance(tool_call['name'], str):
            errors.append("Tool call 'name' must be a string")
            return False, None, errors
            
        function_name = tool_call['name']
        if function_name not in self.function_registry:
            errors.append(f"Unknown function: {function_name}")
            return False, None, errors
            
        try:
            transformed_data, transformations = self.transformer.transform_to_valid_input(
                self.function_registry[function_name],
                tool_call
            )
            
            # Add transformation info to errors list if any transformations were made
            for t in transformations:
                if t.old_value != t.new_value:
                    errors.append(f"Transformed {t.from_path}: {t.old_value} -> {t.new_value}")
            
            return True, transformed_data, errors
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, None, errors

# Example usage:
def get_query_economic_data(input_data):
    """
    Get economic data based on query parameters.
    
    Input format:
    {
        "name": "string",
        "parameters": {
            "query_type": "string (total_fdi_value_by_sector, total_fdi_value_by_country)",
            "start_year": "string",
            "end_year": "string",
            "countries": "list"
        },
        "chart_type": "string (BarChart, LineChart, PieChart)"
    }
    """
    pass

def get_current_date():
    """
    Get current date.
    
    Input format:
    {
        "name": "string",
        "parameters": {}
    }
    """
    return datetime.datetime.now().strftime("%Y-%m-%d")

# Create extractor and register functions
extractor = ToolCallExtractor()
extractor.register_function("get_query_economic_data", get_query_economic_data)
extractor.register_function("get_current_date", get_current_date)

# Example input string
input_string = """ {"name": "get_current_date", "parameters": {}} 
{"name": "get_query_economic_data", "parameters": {"query_type": "total_fdi_value_by_country", "parameters": {"start_year": "2020", "end_year": "2024", "countries": "['Singapore', 'Malaysia', 'Brunei Darussalam', 'Cambodia', 'Laos', 'Myanmar', 'Thailand', 'Philippines', 'Vietnam']"}, "chart_type": "BarChart"}}<|eot_id|>"""

# Extract and validate tool calls
tool_calls = extractor.extract_tool_calls(input_string)
for tool_call in tool_calls:
    is_valid, transformed_data, errors = extractor.validate_and_transform_tool_call(tool_call)
    print(f"\nTool Call: {tool_call['name']}")
    print(f"Valid: {is_valid}")
    if transformed_data:
        print(f"Transformed data: {json.dumps(transformed_data, indent=2)}")
    if errors:
        print("Messages:")
        for error in errors:
            print(f"- {error}")