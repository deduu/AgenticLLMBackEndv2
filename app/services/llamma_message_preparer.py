# app/services/llamma_message_preparer.py
from typing import List, Dict, Any
from app.services.base_message_preparer import BaseMessagePreparer

class llamma_Message_Preparer(BaseMessagePreparer):
    def __init__(self, tool_prompt: str):
        super().__init__(tool_prompt=tool_prompt)

    def prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # llamma-specific message preparation
        return messages  # Modify as needed
