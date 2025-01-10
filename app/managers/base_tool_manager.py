# app/managers/base_tool_manager.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class BaseToolManager(ABC):
    @abstractmethod
    async def handle_tool_calls(
        self, 
        initial_response: str, 
        messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        pass
