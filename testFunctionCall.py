# app/dependencies.py
import os
import torch
from dotenv import load_dotenv
from app.models.model_pool import ParallelModelPool
import datetime, logging
from app.utils.message_utils import function_registry
from app.caller.function_caller import FunctionCaller

logger = logging.getLogger(__name__)
load_dotenv()  # Load environment variables from .env

MODEL_PATH = os.getenv("MODEL_PATH", "meta-llama/Llama-3.1-8B-Instruct")
NUM_INSTANCES = int(os.getenv("NUM_INSTANCES", torch.cuda.device_count() or 1))

model_pool = ParallelModelPool(MODEL_PATH, num_instances=1, devices=["cuda:0"])

async def main():
    """
    Main function for the application.

    This function calls the model pool to generate a response based on the provided 
    messages and available tools. Finally, it prints the response.
    """
    function_caller = FunctionCaller(llm = model_pool, tools = function_registry.values())
    # print(f"Messages: {messages}")
    # print(get_current_date)
    response = await function_caller.execute("what is the current date?")
    print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())  # Run the main function asynchronously