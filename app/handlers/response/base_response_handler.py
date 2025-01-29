
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseResponseHandler(ABC):
    @abstractmethod
    async def handle_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

        pass