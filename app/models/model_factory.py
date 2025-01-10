# app/models/model_factory.py
from typing import Dict, Any
from app.models.base_model import BaseModel
from app.models.qwen_model import QwenModel
from app.models.llamma_model import llammaModel

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
                dtype=config.get("dtype", "float16")
            )
        elif model_type == "llamma":
            return llammaModel(
                model_path=config["model_path"],
                device=config["device"],
                dtype=config.get("dtype", "float16")
            )
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
