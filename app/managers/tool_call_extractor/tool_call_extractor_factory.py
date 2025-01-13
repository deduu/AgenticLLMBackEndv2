from .llamma_tool_call_extractor import LlamaToolCallExtractor
from .qwen_tool_call_extractor import QwenToolCallExtractor


class ToolCallExtractorFactory:
    @staticmethod
    def get_tool_call_extractor(model_type):
        if model_type == "llamma":
            return LlamaToolCallExtractor()
        elif model_type == "qwen":
            return QwenToolCallExtractor()
        else:   
            raise ValueError(f"Unsupported model type: {model_type}")
        