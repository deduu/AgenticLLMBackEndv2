# app/services/base_message_preparer.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ..utils.system_prompt import tool_prompt as default_tool_prompt

class BaseMessagePreparer(ABC):
    def __init__(self, tool_prompt: str=None):
        self.default_tool_prompt = tool_prompt or default_tool_prompt
        
    @abstractmethod
    def prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass
