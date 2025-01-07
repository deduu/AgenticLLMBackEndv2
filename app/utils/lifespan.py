# app/utils/lifespan.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    try:
        yield
    except Exception as e:
        logger.error(f"Error during application lifespan: {e}")
        raise e
    finally:
        logger.info("Application stopped.")
