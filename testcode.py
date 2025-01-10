# BaseMessagePreparer with fallback for tool_prompt
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from app.utils.system_prompt import tool_prompt as default_tool_prompt


class BaseMessagePreparer(ABC):
    def __init__(self, tool_prompt: str = None):
        # Use a default fallback value if tool_prompt is not provided
        self.default_tool_prompt = tool_prompt or default_tool_prompt
        print(f"Using tool_prompt: {self.default_tool_prompt}")

    @abstractmethod
    def prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass


# llamma_Message_Preparer with optional tool_prompt
class llamma_Message_Preparer(BaseMessagePreparer):
    def __init__(self, tool_prompt: str = None):
        # Pass the tool_prompt to the base class, allowing None
        super().__init__(tool_prompt=tool_prompt)

    def prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Example usage of the tool_prompt
        print(f"Using tool_prompt: {self.default_tool_prompt}")
        return messages  # Modify as needed


preparer = llamma_Message_Preparer(tool_prompt="You are a helpful assistant.")