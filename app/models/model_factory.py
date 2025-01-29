# app/models/model_factory.py
from typing import Dict, Any
from app.models.base_model import BaseModel
from app.models.qwen_model import QwenModel
from app.models.llamma_model import llammaModel
from app.models.deepseek_model import deepSeekLlamaModel

class ModelFactory:
    """
    Factory to create model instances based on model type.
    """
    
    @staticmethod
    def create_model(model_type: str, config: Dict[str, Any]) -> BaseModel:
        if model_type == "qwen":
            return QwenModel(
                model_path=config["model_path"],
                device=config["device"],
                dtype=config.get("dtype", "float16"),
                quantization=config.get("quantization", "4bit"),
                cot = config.get("cot", False)
            )
        elif model_type == "llamma":
            return llammaModel(
                model_path=config["model_path"],
                device=config["device"],
                dtype=config.get("dtype", "float16"),
                quantization=config.get("quantization", "None"),
                cot = config.get("cot", False)
            )
        elif model_type == "llamma_small":
             return llammaModel(
                model_path=config["model_path"],
                device=config["device"],
                dtype=config.get("dtype", "float16"),
                quantization=config.get("quantization", "None"),
                cot = config.get("cot", False)
            )
        elif model_type == "deepseek":
#             system_prompt = """You are an expert at reasoning and problem-solving. Given a context and a question, you will reason step by step to arrive at the answer. Base your answer *solely* on the information provided in the context. If the answer cannot be directly found in the context, explain how you arrived at the answer by making logical inferences from the context. Let's think step by step.
# Jawablah *hanya* dalam bahasa Indonesia. Jangan gunakan bahasa lain dalam respons Anda.
# """
            return deepSeekLlamaModel(
                model_path=config["model_path"],
                device=config["device"],
                dtype=config.get("dtype", "float16"),
                quantization=config.get("quantization", "None"),
                cot = config.get("cot", False)
            )

        else:
            raise ValueError(f"Unsupported model type: {model_type}")
