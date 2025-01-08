# app/handlers/response_handler.py
from typing import List, Dict
from app.utils.message_utils import rename_parameters_to_arguments, convert_dates_to_strings

class ResponseHandler:
    @staticmethod
    def handle_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        messages = rename_parameters_to_arguments(messages)
        messages = convert_dates_to_strings(messages)
        return messages