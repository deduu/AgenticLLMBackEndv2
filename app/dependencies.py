# app/dependencies.py
import os
import torch
from dotenv import load_dotenv
from .models.model_pool import ParallelModelPool

load_dotenv()  # Load environment variables from .env

MODEL_PATH = os.getenv("MODEL_PATH", "meta-llama/Llama-3.1-8B-Instruct")
NUM_INSTANCES = int(os.getenv("NUM_INSTANCES", torch.cuda.device_count() or 1))

model_pool = ParallelModelPool(MODEL_PATH, num_instances=1, devices = ["cuda:0"])
