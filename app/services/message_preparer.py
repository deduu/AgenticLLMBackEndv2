from typing import List, Dict, Optional
from app.utils.system_prompt import tool_prompt

class MessagePreparer:
    def __init__(self, tool_prompt: str = tool_prompt):
        self.default_tool_prompt = tool_prompt

    def prepare_messages(
        self, 
        subquery: str, 
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        tool_calling_prompt = system_prompt if system_prompt else self.default_tool_prompt
        messages = [{"role": "system", "content": tool_calling_prompt}]
        
        if subquery:
            messages.append({"role": "user", "content": subquery})
        
        return messages