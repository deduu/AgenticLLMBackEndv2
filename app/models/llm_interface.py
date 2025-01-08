# app/models/llm_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMInterface(ABC):
    @property
    @abstractmethod
    def tokenizer(self):
        pass

    @property
    @abstractmethod
    def device(self):
        pass

    @abstractmethod
    async def generate_function_call(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Any]
    ) -> str:
        """
        Generate a response using the model pool.
        
        :param messages: The messages to send to the LLM.
        :param max_new_tokens: The maximum number of tokens to generate.
        :return: The generated response as a string.
        """
        pass

    @abstractmethod
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        max_new_tokens: int = 128
    ) -> str:
        """
        Generate a response based on the provided messages.
        
        :param messages: The messages to send to the LLM.
        :param max_new_tokens: The maximum number of tokens to generate.
        :return: The generated response as a string.
        """
