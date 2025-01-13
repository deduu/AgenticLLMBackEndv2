from .base_tool_call_extractor import BaseToolCallExtractor

class LlamaToolCallExtractor(BaseToolCallExtractor):
    def __init__(self):
        """
        Initialize the Llama-specific extractor with its unique patterns.
        """
        super().__init__(
            complete_pattern=r'<\|python_tag\|>(.*?)<\|eom_id\|>',
            partial_pattern=r'(.*?)<\|(?:eom_id|eot_id)\|>'
        )