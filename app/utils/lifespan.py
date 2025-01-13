# app/utils/lifespan.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.dependencies import model_pool
from app.caller.function_caller import FunctionCaller
from app.crud.employee import initialize_employee_database_sessions
from ..utils.message_utils import function_registry

logger = logging.getLogger(__name__)

async def setup_function_call():
    await initialize_employee_database_sessions()
    function_caller = FunctionCaller(llm=model_pool, tools=function_registry.values())

    return function_caller

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    function_caller = await setup_function_call()
    app.state.function_caller = function_caller
    try:
        
        yield
    except Exception as e:
        logger.error(f"Error during application lifespan: {e}")
        raise e
    finally:
        logger.info("Application stopped.")
