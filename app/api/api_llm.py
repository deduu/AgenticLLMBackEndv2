# app/routes/generate.py
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Union
import logging, json
from ..utils.message_utils import function_registry
from ..schemas.frontend import FrontendPayload
from ..schemas.llm_request import LLMRequest
from ..models.model_pool import ParallelModelPool
from ..dependencies import small_model_pool, medium_model_pool

logger = logging.getLogger(__name__)

router = APIRouter()

# Assume model_pool is initialized elsewhere and imported


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
        response_stream = medium_model_pool.generate_text_stream(
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

@router.post("/llamma/stream")
async def llamma_llm_stream(request: Request, body: LLMRequest):

     # Access the loaded model from app.state
    agentic_system = request.app.state.agentic_system
    llm = agentic_system.medium_llm
    
    logger.info(f"choosen model: {body.model}")
    
    function_call_only_flag = True
  
    retrieved_sources= {}
    if body.model == "local_agentic_model" and body.collections:
        logger.info("Agentic initiating...")
        function_call_only_flag = False
        # Try to understand the query
        subqueries = await agentic_system.understand(body)
        
        # Process the subqueries
        retrieved_sources = await agentic_system.process(subqueries, body)

    if function_call_only_flag and body.model == "local_model" and body.function_call:
        logger.info("Function calling...")
        body.query = await llm.query_moderator(body.query, body.history_messages)
        tool_response = await agentic_system.function_caller.execute(subquery=body.query, system_prompt = body.tool_prompt, tools=function_registry.values())
        retrieved_sources["Subquery-1"] = {
            "Source":  tool_response,
            "Type": "Action"
        }
    # tool_response = await function_caller.execute(subquery=body.query)


    # retrieved_sources["Subquery-1"] = {
    #         "Source":  tool_response,
    #         "Type": "Action"
    #     }
    # logger.info(f"retrieved_sources: {retrieved_sources}")
    # logger.info(f"query: {body.query}")
    # logger.info(f"history_messages: {body.history_messages}")

    async def stream_response():
        for key, value in retrieved_sources.items():
            if value.get("Type") == "Action":
                sources = value.get("Source", [])
                if not isinstance(sources, list):
                    sources = [sources]
                
                for source in sources:
                    chart_data = source.get("chartData", []) 
                    if chart_data:
                        yield f"data: {json.dumps({'chartData': chart_data})}\n\n"
                
        logger.info("Starting stream response generation")
        
        async for chunk in llm.generate_text_stream(
            query=body.query,
            context=retrieved_sources,
            history_messages=body.history_messages,
            max_new_tokens=body.max_new_tokens,
            temperature=body.temperature,
            top_p=body.top_p,
            timeout=None
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")