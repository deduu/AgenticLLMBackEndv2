# app/main.py
from fastapi import FastAPI, WebSocket
from fastapi import Request
import asyncio

from fastapi.middleware.cors import CORSMiddleware

from .utils.lifespan import lifespan
from .utils.logging_config import setup_logging
from .api import api_llm, api_status, api_docs

# Setup logging
logger = setup_logging()

# Create FastAPI instance with lifespan
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_llm.router, prefix="/v1", tags=["llm"])
app.include_router(api_status.router)
app.include_router(api_docs.file_load_router, prefix="/v1", tags=["file_load"])

# Root endpoint (optional)
@app.get("/")
async def root():
    return {"message": "LLM API is running."}