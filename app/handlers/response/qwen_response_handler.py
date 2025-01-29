from typing import List, Dict, Any

from .base_response_handler import BaseResponseHandler
from ...utils.message_utils import rename_parameters_to_arguments, convert_dates_to_strings



class Qwen_Response_Handler(BaseResponseHandler):
    async def handle_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        messages = rename_parameters_to_arguments(messages)
        messages = convert_dates_to_strings(messages)
        return messages
