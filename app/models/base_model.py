# app/models/base_model.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from app.utils.system_prompt import agentic_prompt as default_system_prompt

class BaseModel(ABC):
    """
    Abstract base class for all models.
    """
    
    def __init__(self, model_path: str, device: str, system_prompt: str=None):
        self.model_path = model_path
        self.device = device
        self.system_prompt = system_prompt or default_system_prompt
        print(f"Using system_prompt: {self.system_prompt}")
    
    @abstractmethod
    async def generate_function_call(self, messages: List[Dict[str, str]], tools: List[Any]) -> str:
        pass
    
    @abstractmethod
    async def generate_text_stream(self, query: str, **kwargs):
        pass
    
    @abstractmethod
    async def generate_text(self, messages: List[Dict[str, str]], max_new_tokens: int) -> str:
        pass
