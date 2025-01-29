
from .llamma_response_handler import llamma_Response_Handler
from .qwen_response_handler import Qwen_Response_Handler
from .base_response_handler import BaseResponseHandler
from .deepseek_response_handler import deepSeeklllama_Response_Handler

class ResponseHandlerFactory:
    @staticmethod
    def get_response_handler(model_type: str) -> BaseResponseHandler:
        if model_type == "llamma" or model_type == "llamma_small":
            return llamma_Response_Handler()
        elif model_type == "qwen":
            return Qwen_Response_Handler()
        elif model_type == "deepseek":
            return deepSeeklllama_Response_Handler()
        else:
            raise ValueError(f"Unsupported model type for ResponseHandler: {model_type}")