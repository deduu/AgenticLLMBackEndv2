import re
import json
import inspect
import ast
import difflib
from typing import Any, Dict, Optional, Tuple, Union, List
from dataclasses import dataclass
from enum import Enum
import datetime

class SchemaTransformer:
    def __init__(self):
        self.transformations = []
        
    @dataclass
    class Transformation:
        from_path: str
        to_path: str
        old_value: Any
        new_value: Any
        
    def find_closest_match(self, value: str, valid_values: list[str]) -> str:
        if not valid_values:
            return value
        return difflib.get_close_matches(value, valid_values, n=1, cutoff=0.6)[0] if difflib.get_close_matches(value, valid_values, n=1, cutoff=0.6) else value

    def extract_valid_values_from_docstring(self, docstring: str, field_name: str) -> list[str]:
        try:
            field_start = docstring.find(f"{field_name}:")
            if field_start == -1:
                return []
            
            values_start = docstring.find("(", field_start)
            if values_start == -1:
                values_start = docstring.find(":", field_start)
            if values_start == -1:
                return []
                
            values_end = docstring.find(")", values_start)
            if values_end == -1:
                values_end = docstring.find("\n", values_start)
            if values_end == -1:
                return []
                
            values_str = docstring[values_start + 1:values_end]
            return [v.strip() for v in values_str.split(",")]
        except:
            return []

    def transform_value(self, value: Any, expected_type: str) -> Any:
        try:
            if expected_type == "string":
                return str(value)
            elif expected_type == "integer":
                return int(float(value))
            elif expected_type == "float":
                return float(value)
            elif expected_type == "boolean":
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes")
                return bool(value)
            elif expected_type == "list":
                if isinstance(value, str):
                    try:
                        return ast.literal_eval(value)
                    except:
                        return [value]
                elif isinstance(value, list):
                    return value
                else:
                    return [value]
            elif expected_type == "dict":
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except:
                        return {"value": value}
                elif isinstance(value, dict):
                    return value
                else:
                    return {"value": value}
            return value
        except:
            return value

    def find_value_in_nested_dict(self, data: Dict, key: str) -> Tuple[Any, str]:
        def _search(d: Dict, path: str = "") -> Tuple[Any, str]:
            if not isinstance(d, dict):
                return None, ""
                
            for k, v in d.items():
                current_path = f"{path}.{k}" if path else k
                if k == key:
                    return v, current_path
                elif isinstance(v, dict):
                    found_value, found_path = _search(v, current_path)
                    if found_value is not None:
                        return found_value, found_path
            return None, ""
            
        return _search(data)

    def transform_data(self, data: Dict, schema: Dict, docstring: str, current_path: str = "") -> Dict:
        result = {}
        
        for key, expected in schema.items():
            new_path = f"{current_path}.{key}" if current_path else key
            
            value, value_path = self.find_value_in_nested_dict(data, key)
            
            if value is None and key in data:
                value = data[key]
                value_path = new_path
            
            if isinstance(expected, dict):
                if value is None:
                    value = {}
                if not isinstance(value, dict):
                    value = {"value": value}
                result[key] = self.transform_data(value, expected, docstring, new_path)
            else:
                if value is not None:
                    transformed_value = self.transform_value(value, expected)
                    
                    if expected == "string":
                        valid_values = self.extract_valid_values_from_docstring(docstring, key)
                        if valid_values:
                            transformed_value = self.find_closest_match(str(transformed_value), valid_values)
                    
                    if transformed_value != value:
                        self.transformations.append(self.Transformation(
                            from_path=value_path or new_path,
                            to_path=new_path,
                            old_value=value,
                            new_value=transformed_value
                        ))
                    result[key] = transformed_value
                else:
                    default_value = self.get_default_value(expected)
                    result[key] = default_value
                    self.transformations.append(self.Transformation(
                        from_path=new_path,
                        to_path=new_path,
                        old_value=None,
                        new_value=default_value
                    ))
        
        return result

    def get_default_value(self, type_str: str) -> Any:
        defaults = {
            "string": "",
            "integer": 0,
            "float": 0.0,
            "boolean": False,
            "list": [],
            "dict": {}
        }
        return defaults.get(type_str, None)

    def transform_to_valid_input(self, function, input_data: Union[str, Dict]) -> Tuple[Dict, list[Transformation]]:
        self.transformations = []
        
        try:
            if isinstance(input_data, str):
                data = json.loads(input_data)
            else:
                data = input_data
                
            docstring = inspect.getdoc(function)
            if not docstring:
                raise ValueError("Function must have a docstring")
                
            schema_start = docstring.find("Input format:")
            if schema_start == -1:
                schema_start = docstring.find("```")
            if schema_start == -1:
                raise ValueError("Could not find schema definition in docstring")
                
            schema_text = docstring[schema_start:]
            start_brace = schema_text.find("{")
            end_brace = schema_text.rfind("}")
            
            if start_brace == -1 or end_brace == -1:
                raise ValueError("Could not find JSON structure in docstring")
                
            schema_json = schema_text[start_brace:end_brace + 1]
            
            schema_json = schema_json.replace("str,", '"string",')
            schema_json = schema_json.replace("int,", '"integer",')
            schema_json = schema_json.replace("float,", '"float",')
            schema_json = schema_json.replace("bool,", '"boolean",')
            schema_json = schema_json.replace("list,", '"list",')
            schema_json = schema_json.replace("dict,", '"dict",')
            
            schema = json.loads(schema_json)
            
            transformed_data = self.transform_data(data, schema, docstring)
            
            return transformed_data, self.transformations
            
        except Exception as e:
            raise ValueError(f"Transformation error: {str(e)}")