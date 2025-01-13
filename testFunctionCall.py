# app/dependencies.py
import os
import torch
from dotenv import load_dotenv
from app.models.parallel_model_pool import ParallelModelPool
import logging
from app.utils.message_utils import function_registry
from app.caller.function_caller import FunctionCaller
from app.crud.employee import initialize_employee_database_sessions
from app.config_loader import load_config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()  # Load environment variables from .env

MODEL_PATH = "Qwen/QwQ-32B-Preview"
NUM_INSTANCES = int(os.getenv("NUM_INSTANCES", torch.cuda.device_count() or 1))
logger.info(f"Model: {MODEL_PATH}")
config_path = "./config.yaml"
model_configs = load_config(config_path)
print(f"Model configs: {model_configs}")

model_pool = ParallelModelPool(model_configs=model_configs, num_instances=1)



async def main():
    """
    Main function for the application.

    This function calls the model pool to generate a response based on the provided 
    messages and available tools. Finally, it prints the response.
    """
    await initialize_employee_database_sessions()
    function_caller = FunctionCaller(llm = model_pool, tools = function_registry.values())
    # print(f"Messages: {messages}")
    # print(get_current_date)
    response = await function_caller.execute("what is the average age of employees in the company?")
    print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())  # Run the main function asynchronously