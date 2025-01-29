from typing import Optional, List
from pydantic import BaseModel, Field

class LLMRequest(BaseModel):
    query: str = Field(..., description="User input for the model to process")
    history_messages: Optional[str] = Field("", description="Optional message history to provide context")
    system_prompt: Optional[str] = Field(None, description="Optional custom system prompt")
    max_new_tokens: int = Field(1024, gt=0, description="Maximum number of new tokens to generate")
    temperature: float = Field(0.7, gt=0.0, le=1.0, description="Sampling temperature")
    top_k: int = Field(50, ge=0, description="Top-k sampling")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Top-p (nucleus) sampling")
    collections: Optional[List[str]] = Field(None, description="Optional list of collection IDs to use for chatbot")
    function_call: Optional[bool] = Field(None, description="Optional function call to use for chatbot") 
    tool_prompt: Optional[str] = Field(None, description="Optional tool prompt to use for chatbot")
    model: Optional[str] = Field(None, description="Optional model to use for chatbot")