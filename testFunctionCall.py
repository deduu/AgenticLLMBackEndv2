# app/dependencies.py
import os
import torch
from dotenv import load_dotenv
# from app.models.parallel_model_pool import ParallelModelPool
from app.models.AnyModel import AnyModel
import logging
from app.utils.message_utils import function_registry
from app.caller.function_caller import FunctionCaller
from app.crud.employee import initialize_employee_database_sessions
from app.crud.economic_fdi import initialize_fdi_database_sessions
from app.config_loader import load_model_configs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()  # Load environment variables from .env

config_path = "./config.yaml"
medium_model_configs =  load_model_configs(config_path, "small")
print(f"Medium model configs: {medium_model_configs}")

model_pool = AnyModel(model_configs=medium_model_configs, num_instances=1)



async def main():
    """
    Main function for the application.

    This function calls the model pool to generate a response based on the provided 
    messages and available tools. Finally, it prints the response.
    """
    await initialize_employee_database_sessions()
    await initialize_fdi_database_sessions()
    function_caller = FunctionCaller(llm = model_pool, tools = function_registry.values())
    # print(f"Messages: {messages}")
    # print(get_current_date)
    # response = await function_caller.execute("what are the trends in FDI in Indonesia across sectors from ASEAN countries between 2010 and 2023?")
    response = await function_caller.execute("What is the current date and Which country has the biggest contributor in FDI in Indonesia from ASEAN countries between 2020 and 2024?")
    print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())  # Run the main function asynchronously