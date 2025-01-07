# app/schemas/llm_request.py
from typing import List, Optional, Dict
from pydantic import BaseModel

class LLMRequest(BaseModel):
    query: str
    history_messages: Optional[List[Dict[str, str]]] = None
    max_new_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
