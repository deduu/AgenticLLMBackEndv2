import re
import json


class BaseToolCallExtractor:
    def __init__(self, complete_pattern, partial_pattern):
        """
        Initialize the base extractor with model-specific patterns.
        """
        self.complete_pattern = re.compile(complete_pattern, re.DOTALL)
        self.partial_pattern = re.compile(partial_pattern, re.DOTALL)

    def _clean_and_parse_json(self, json_str):
        """
        Clean and parse a JSON string, handling common formatting issues.
        """
        try:
            json_str = json_str.strip()
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
        potential_jsons = text.split(';')
        for json_str in potential_jsons:
            parsed_obj = self._clean_and_parse_json(json_str)
            if parsed_obj:
                json_objects.append(parsed_obj)
        return json_objects

    def extract_tool_calls(self, input_string):
        """
        Extract tool calls from input string, handling various inconsistent formats.
        """
        tool_calls = []

        # Check for complete tag structure
        complete_matches = self.complete_pattern.findall(input_string)
        if complete_matches:
            for match in complete_matches:
                tool_calls.extend(self._extract_json_objects(match))
            return tool_calls

        # Check for partial tag structure
        partial_matches = self.partial_pattern.findall(input_string)
        if partial_matches:
            for match in partial_matches:
                tool_calls.extend(self._extract_json_objects(match))
            return tool_calls

        # No tags at all, try to parse the whole string
        tool_calls.extend(self._extract_json_objects(input_string))
        return tool_calls

    def validate_tool_call(self, tool_call):
        """
        Validate if a tool call has the required fields.
        """
        return (
            isinstance(tool_call, dict)
            and 'name' in tool_call
            and isinstance(tool_call['name'], str)
        )
