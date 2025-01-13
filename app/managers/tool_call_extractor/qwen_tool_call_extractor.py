from .base_tool_call_extractor import BaseToolCallExtractor

class QwenToolCallExtractor(BaseToolCallExtractor):
    def __init__(self):
        """
        Initialize the Qwen-specific extractor with its unique patterns.
        """
        super().__init__(
            # Complete pattern to capture JSON-like structure within <tool_call> tags
            complete_pattern=r'<tool_call>(\{.*?\})<\/tool_call>',
            
            # Partial pattern to capture JSON-like structure for partial matches
            partial_pattern=r'<tool_call>(.*?)<\/tool_call>'
        )
