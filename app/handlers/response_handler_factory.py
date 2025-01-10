
from .llamma_response_handler import llamma_Response_Handler
from .base_response_handler import BaseResponseHandler

class ResponseHandlerFactory:
    @staticmethod
    def get_response_handler(model_type: str) -> BaseResponseHandler:
        if model_type == "llamma":
            return llamma_Response_Handler()
        else:
            raise ValueError(f"Unsupported model type for ResponseHandler: {model_type}")