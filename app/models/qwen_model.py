# app/models/qwen_model.py
from app.models.base_model import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict, Any, Optional
import torch
import logging


logger = logging.getLogger(__name__)

class QwenModel(BaseModel):
     def __init__(self, model_path: str, device: str, dtype=torch.float16):
        super().__init__(model_path, device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, 
            torch_dtype=dtype
        ).to(device)
        logger.info(f"Loaded Qwen model on {device}")
    