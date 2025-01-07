# app/routes/generate.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Union
import logging
from ..schemas.frontend import FrontendPayload
from ..schemas.llm_request import LLMRequest
from ..models.model_pool import ParallelModelPool

logger = logging.getLogger(__name__)

router = APIRouter()

# Assume model_pool is initialized elsewhere and imported
from ..dependencies import model_pool

@router.post("/generate")
async def generate(request: FrontendPayload):
    try:
        # Parse `history_messages` if it's a string
        if isinstance(request.history_messages, str):
            history_messages = [{"role": "user", "content": request.history_messages}]
        else:
            history_messages = request.history_messages

        # Prepare the backend request
        llm_request = LLMRequest(
            query=request.query,
            history_messages=history_messages,
            temperature=request.temperature,
            top_p=request.top_p
        )
        context = {}

        # Pass the parsed request to the model
        response_stream = model_pool.generate_text_stream(
            query=llm_request.query,
            context = context,
            history_messages=llm_request.history_messages,
            max_new_tokens=llm_request.max_new_tokens,
            temperature=llm_request.temperature,
            top_p=llm_request.top_p
        )

        # Wrap response stream in StreamingResponse
        return StreamingResponse(response_stream, media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
