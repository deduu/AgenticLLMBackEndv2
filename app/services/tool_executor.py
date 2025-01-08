import re
import json
import datetime
class ToolCallExtractor:
    def __init__(self):
        # Pattern for complete tag structure
        self.complete_pattern = re.compile(r'<\|python_tag\|>(.*?)<\|eom_id\|>', re.DOTALL)
        # # Pattern for partial tag structure (ending with eom_id)
        # self.partial_pattern = re.compile(r'(.*?)<\|eom_id\|>', re.DOTALL)
        # Pattern for partial tag structure ending with either <|eom_id|> or <|eot_id|>
        self.partial_pattern = re.compile(r'(.*?)<\|(?:eom_id|eot_id)\|>', re.DOTALL)

        
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

    def _extract_json_objects(self, text):
        """
        Extract and parse multiple JSON objects from a string.
        """
        json_objects = []
        # Split by semicolon to handle multiple JSON objects
        potential_jsons = text.split(';')
        
        for json_str in potential_jsons:
            parsed_obj = self._clean_and_parse_json(json_str)
            if parsed_obj:
                json_objects.append(parsed_obj)
                
        return json_objects

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