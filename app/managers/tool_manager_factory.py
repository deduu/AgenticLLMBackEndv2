# app/managers/tool_manager_factory.py
from app.managers.base_tool_manager import BaseToolManager
from app.managers.llamma_tool_manager import LlammaToolManager
from app.managers.qwen_tool_manager import QwenToolManager
from app.managers.deepseek_tool_manager import deepSeekLlammaToolManager
# from app.managers.gemini_tool_manager import GeminiToolManager

class ToolManagerFactory:
    @staticmethod
    def get_tool_manager(model_type: str) -> BaseToolManager:
        if model_type == "llamma" or model_type == "llamma_small":
            return LlammaToolManager()
        elif model_type == "qwen":
            return QwenToolManager()
        elif model_type == "deepseek":
            return deepSeekLlammaToolManager()
        else:
            raise ValueError(f"Unsupported model type for ToolManager: {model_type}")
