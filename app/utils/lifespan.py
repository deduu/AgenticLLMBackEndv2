# app/utils/lifespan.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

# from app.dependencies import model_pool
from app.caller.function_caller import FunctionCaller
from app.crud.employee import initialize_employee_database_sessions
from app.crud.economic_fdi import initialize_fdi_database_sessions
from ..utils.message_utils import function_registry
from ..dependencies import agentic, rag_system
logger = logging.getLogger(__name__)

# async def setup_function_call():
#     await initialize_employee_database_sessions()
#     await initialize_fdi_database_sessions()
#     function_caller = FunctionCaller(llm=model_pool, tools=function_registry.values())

#     return function_caller

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agentic_system = agentic
    app.state.rag_system = agentic.rag
    logger.info("Starting application...")
    # function_caller = await setup_function_call()
    # app.state.function_caller = function_caller
    try:
        agentic.rag.load_state("rag_state")
        yield
    except FileNotFoundError:
            print("No existing state found. Starting fresh.")
            yield
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise e
    finally:
        logger.info("Application stopped.")
         # Save state when done
        app.state.rag_system.save_state("rag_state")
        print("State saved.")
