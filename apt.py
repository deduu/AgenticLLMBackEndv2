import json
import ast
import difflib
import inspect
import re
from typing import Any, Dict, Tuple, Union
from dataclasses import dataclass
from enum import Enum

# === SchemaTransformer class (as provided) ===

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
        """Find the closest matching string using difflib."""
        if not valid_values:
            return value
        return difflib.get_close_matches(value, valid_values, n=1, cutoff=0.6)[0] if difflib.get_close_matches(value, valid_values, n=1, cutoff=0.6) else value

    def extract_valid_values_from_docstring(self, docstring: str, field_name: str) -> list[str]:
        """Extract valid values for a field from docstring if specified."""
        try:
            # Look for field in docstring with valid values
            field_start = docstring.find(f"{field_name}:")
            if field_start == -1:
                return []
            
            # Look for valid values in parentheses or after colon
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
        """Transform a value to match the expected type."""
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
        """
        Recursively search for a key in nested dictionaries.
        Returns (value, path) if found, (None, "") if not found.
        """
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
        """
        Transform data to match the schema, tracking all transformations.
        Returns transformed data.
        """
        result = {}
        
        # Handle schema keys first
        for key, expected in schema.items():
            new_path = f"{current_path}.{key}" if current_path else key
            
            # Try to find the value in the input data, including nested structures
            value, value_path = self.find_value_in_nested_dict(data, key)
            
            if value is None and key in data:
                value = data[key]
                value_path = new_path
            
            if isinstance(expected, dict):
                # Recursively transform nested objects
                if value is None:
                    value = {}
                if not isinstance(value, dict):
                    value = {"value": value}
                result[key] = self.transform_data(value, expected, docstring, new_path)
            else:
                if value is not None:
                    # Transform value to match expected type
                    transformed_value = self.transform_value(value, expected)
                    
                    # For string fields, try to match with valid values from docstring
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
                    # Provide default values for missing fields
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
        """Provide default values for different types."""
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
        """
        Transform invalid input into valid input based on function's docstring schema.
        Returns (transformed_data, transformations).
        """
        self.transformations = []
        
        try:
            # Parse input JSON if string
            if isinstance(input_data, str):
                data = json.loads(input_data)
            else:
                data = input_data
                
            # Get schema and docstring
            docstring = inspect.getdoc(function)
            if not docstring:
                raise ValueError("Function must have a docstring")
                
            # Extract schema
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
            
            # Use regex to replace Python type tokens with our JSON string equivalents
            pattern = r':\s*(str|int|float|bool|list|dict)([\s,\}])'
            def repl(m):
                token = m.group(1)
                trailing = m.group(2)
                mapping = {
                    'str': '"string"',
                    'int': '"integer"',
                    'float': '"float"',
                    'bool': '"boolean"',
                    'list': '"list"',
                    'dict': '"dict"'
                }
                return f': {mapping[token]}{trailing}'
            
            schema_json = re.sub(pattern, repl, schema_json)
            
            # Now convert the JSON
            schema = json.loads(schema_json)
            
            # Transform data
            transformed_data = self.transform_data(data, schema, docstring)
            
            return transformed_data, self.transformations
            
        except Exception as e:
            raise ValueError(f"Transformation error: {str(e)}")

# === Sample function with a docstring that defines the input schema ===

def sample_function(data):
    """
    Process the data.

    Input format:
    {
      "name": str,
      "age": int,
      "active": bool,
      "preferences": {
          "color": "str (red, green, blue)",
          "foods": list
      }
    }
    """
    pass

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

# === Test scenarios ===

if __name__ == "__main__":
    transformer = SchemaTransformer()
    
    # Define several test cases as tuples of (description, input_data)
    test_cases = [
        (
            "Test 1: All fields provided with values as strings (requiring type conversion). "
            "Note: 'age' is a string that should become an integer and 'active' is a string.",
            {
                "name": "Alice",
                "age": "30",
                "active": "True",
                "preferences": {
                    "color": "gren",  # misspelled: should match "green"
                    "foods": "[\"apple\", \"banana\"]"  # list provided as a string
                }
            }
        ),
        (
            "Test 2: Missing some fields (e.g. 'active' and nested 'foods' missing).",
            {
                "name": "Bob",
                "age": 22,
                "preferences": {
                    "color": "blue"  # correct spelling and already a string
                }
            }
        ),
        (
            "Test 3: Nested structure is not a dict (preferences provided as a string).",
            {
                "name": "Charlie",
                "age": 28,
                "active": False,
                "preferences": "[{'color': 'red', 'foods': ['pizza', 'pasta']}]"  # malformed nested data
            }
        ),
        (
            "Test 4: Incorrect types and extra nested structure. The 'age' field is a float string and "
            "the 'active' field is given as 1. 'color' is misspelled and should be corrected to the closest valid.",
            {
                "name": 123,  # numeric but should become string "123"
                "age": "45.0",
                "active": 1,
                "preferences": {
                    "color": "ree",  # close to "red"
                    "foods": ["sushi", "ramen"]
                }
            }
        )
        ,
        (
            "Hello world",
            {
                "name": "get_query_economic_data",
                "parameters": {
                    "query_type": "total_fdi_value_by_country",  # Different from expected
                    "parameters": {
                        "start_year": 2020,  # Integer instead of string
                        "end_year": "2024",
                        "countries": "['Singapore', 'Malaysia']"
                    },
                    "chart_type": "BarChart"  # Incomplete chart type name
                }
            }
        )
    ]
    
    for idx, (desc, input_data) in enumerate(test_cases):
        print(f"\n=== {desc} ===")
        try:
            # You can pass either a dict or a JSON string
            transformed, transformations = transformer.transform_to_valid_input(get_query_economic_data, input_data)
            
            print("Input Data:")
            print(json.dumps(input_data, indent=2))
            print("\nTransformed Data:")
            print(json.dumps(transformed, indent=2))
            
            if transformations:
                print("\nTransformations:")
                for t in transformations:
                    print(f" - From '{t.from_path}': {t.old_value}  -->  To '{t.to_path}': {t.new_value}")
            else:
                print("\nNo transformations applied.")
                
        except Exception as e:
            print(f"Error: {e}")

