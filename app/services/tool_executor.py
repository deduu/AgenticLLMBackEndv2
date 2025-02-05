import re
import json
import datetime
from typing import Any, Dict, List, Optional, Tuple
from app.functions.tool_docstring import *
from .schema_transformer import SchemaTransformer


class ToolCallExtractor:
    def __init__(self):
        # Pattern for complete tag structure
        self.complete_pattern = re.compile(r'<\|python_tag\|>(.*?)<\|eom_id\|>', re.DOTALL)
        # # Pattern for partial tag structure (ending with eom_id)
        # self.partial_pattern = re.compile(r'(.*?)<\|eom_id\|>', re.DOTALL)
        # Pattern for partial tag structure ending with either <|eom_id|> or <|eot_id|>
        self.partial_pattern = re.compile(r'(.*?)<\|(?:eom_id|eot_id)\|>', re.DOTALL)
        self.transformer = SchemaTransformer()
        self.function_registry = {}
        self.register_function("get_query_economic_data", get_query_economic_data)
        self.register_function("get_current_date", get_current_date)
    
    def register_function(self, name: str, function):
        """Register a function with its schema for validation."""
        self.function_registry[name] = function

    def _clean_and_parse_json(self, json_str):
        """
        Clean and parse a JSON string, handling common formatting issues.
        """
        try:
            # Remove any leading/trailing whitespace
            json_str = json_str.strip()
            # Only attempt to parse if it looks like a JSON object
            if json_str.startswith('{'):
                return json.loads(json_str)
            return None
        except json.JSONDecodeError:
            return None
    
    def _extract_json_objects(self, text: str) -> List[Dict]:
        """Extract JSON objects with improved error handling."""
        json_objects = []
        # First attempt: Try parsing as array of objects
        try:
            text = text.strip()
            if text.startswith('[') and text.endswith(']'):
                return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Second attempt: Handle semicolon-separated objects
        if ';' in text:
            for json_str in text.split(';'):
                try:
                    obj = json.loads(json_str.strip())
                    if obj:
                        json_objects.append(obj)
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON segment: {json_str}")
                    
        # Third attempt: Try parsing individual objects using regex
        if not json_objects:
            object_pattern = re.compile(r'\{[^{}]*\}')
            matches = object_pattern.finditer(text)
            for match in matches:
                try:
                    obj = json.loads(match.group())
                    json_objects.append(obj)
                except json.JSONDecodeError:
                    continue

        # Final attempt: Auto-repair common JSON issues
        if not json_objects:
            repaired_text = self._repair_json(text)
            try:
                obj = json.loads(repaired_text)
                if isinstance(obj, dict):
                    json_objects.append(obj)
                elif isinstance(obj, list):
                    json_objects.extend(obj)
            except json.JSONDecodeError:
                pass

        return json_objects

    def _repair_json(self, text: str) -> str:
        """Attempt to repair common JSON formatting issues."""
        # Remove trailing semicolons
        text = re.sub(r';+\s*$', '', text)
        
        # Fix missing closing braces
        open_braces = text.count('{')
        close_braces = text.count('}')
        if open_braces > close_braces:
            text += '}' * (open_braces - close_braces)
            
        # Fix missing quotes around property names
        text = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)
        
        # Fix trailing commas
        text = re.sub(r',\s*([}\]])', r'\1', text)
        
        return text
    
    # def _extract_json_objects(self, text):
    #     json_objects = []
    #     decoder = json.JSONDecoder()
    #     pos = 0
    #     text_length = len(text)
    #     while pos < text_length:
    #         while pos < text_length and text[pos].isspace():
    #             pos += 1
    #         if pos >= text_length:
    #             break
    #         try:
    #             obj, end = decoder.raw_decode(text, pos)
    #             json_objects.append(obj)
    #             pos = end
    #         except json.JSONDecodeError:
    #             pos += 1
    #     return json_objects
    # def _extract_json_objects(self, text):
    #     """
    #     Extract and parse multiple JSON objects from a string.
    #     """
    #     json_objects = []
    #     # Split by semicolon to handle multiple JSON objects
    #     potential_jsons = text.split(';')
        
    #     for json_str in potential_jsons:
    #         parsed_obj = self._clean_and_parse_json(json_str)
    #         if parsed_obj:
    #             json_objects.append(parsed_obj)
                
    #     return json_objects

    def extract_tool_calls(self, input_string):
        """
        Extract tool calls from input string, handling various inconsistent formats.
        
        Args:
            input_string (str): The input string containing tool calls.
        
        Returns:
            list: A list of dictionaries representing the parsed tool calls.
        """
        tool_calls = []
        
        # Case 1: Check for complete tag structure
        complete_matches = self.complete_pattern.findall(input_string)
        if complete_matches:
            for match in complete_matches:
                tool_calls.extend(self._extract_json_objects(match))
            return tool_calls
            
        # Case 2 & 3: Check for partial tag structure (ending with eom_id or eot_id)
        partial_matches = self.partial_pattern.findall(input_string)
        if partial_matches:
            for match in partial_matches:
                tool_calls.extend(self._extract_json_objects(match))
            return tool_calls
            
        # Case 4: No tags at all, try to parse the whole string
        tool_calls.extend(self._extract_json_objects(input_string))
        
        return tool_calls


    def validate_tool_call(self, tool_call):
        """
        Validate if a tool call has the required fields.
        """
        return (
            isinstance(tool_call, dict) and
            'name' in tool_call and
            isinstance(tool_call['name'], str)
        )
    
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
        