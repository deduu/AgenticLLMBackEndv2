import logging
from typing import List, Dict, Any

from ..models.llm_interface import LLMInterface

logger = logging.getLogger(__name__)

class ClosedSourceModel(LLMInterface):
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.api_key = api_key
        self.model_name = model_name
        logger.info(f"ClosedSourceModel initialized with model: {model_name}")

    @property
    def tokenizer(self):
        # Closed-source models typically handle tokenization internally
        return None

    @property
    def model(self):
        # Closed-source models do not expose model directly
        return None

    async def process_user_query(self, messages: List[Dict[str, str]], tools: List[Any]) -> str:
        prompt = self._construct_prompt(messages)
        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=messages,
                max_tokens=150
            )
            logger.info(f"ClosedSourceModel response: {response.choices[0].message['content']}")
            return response.choices[0].message['content']
        except Exception as e:
            logger.error(f"Error with ClosedSourceModel: {e}")
            raise

    def _construct_prompt(self, messages: List[Dict[str, str]]) -> str:
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
