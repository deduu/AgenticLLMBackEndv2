# app/dependencies.py
from sentence_transformers import SentenceTransformer
from app.models.parallel_model_pool import ParallelModelPool
from app.config_loader import load_model_configs, load_embedding_configs
from app.rag.rag_pipeline import RAGSystem
from app.caller.function_caller import FunctionCaller
from app.services.agentic import Agentic
from .utils.message_utils import function_registry

config_path = "./config.yaml"
# large_model_configs =  load_model_configs(config_path, "large")
medium_model_configs =  load_model_configs(config_path, "medium")
small_model_configs =  load_model_configs(config_path, "small")
embedding_configs = load_embedding_configs(config_path)
# print(f"Large model configs: {large_model_configs}")
print(f"Medium model configs: {medium_model_configs}")
print(f"Small model configs: {small_model_configs}")
print(f"Embedding configs: {embedding_configs}")
print(f"embedding use: {embedding_configs[0]["model_id"]}")


medium_model_pool = ParallelModelPool(model_configs=medium_model_configs, num_instances=1)
small_model_pool = ParallelModelPool(model_configs=small_model_configs, num_instances=1)
# large_model_pool = ParallelModelPool(model_configs=large_model_configs, num_instances=1)

embedding_model = SentenceTransformer(embedding_configs[0]["model_id"])

rag_system = RAGSystem(embedding_model=embedding_model)

function_caller = FunctionCaller(llm = small_model_pool, tools=function_registry.values())

agentic = Agentic(small_llm= small_model_pool, medium_llm= medium_model_pool, function_caller = function_caller, rag=rag_system)

