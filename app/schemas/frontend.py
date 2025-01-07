# app/schemas/frontend.py
from typing import List, Optional, Union, Any, Dict
from pydantic import BaseModel

class FrontendPayload(BaseModel):
    query: str
    history_messages: Optional[Union[str, List[Dict[str, str]]]] = None
    system_prompt: Optional[str] = None
    collections: Optional[List[Any]] = []
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: Optional[int] = None  # Optional, can be ignored or used if needed
