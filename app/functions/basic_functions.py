#sqltool.py
import logging
from typing import Optional, Union, Dict, List

import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from datetime import datetime



async def get_current_date() -> str:
    """
    Get the current date.

    This function retrieves the current date.

    Args:
        None
    Returns:
        A dictionary containing the current date as a string in (dd/mm/yyyy) format.
        Example: {'current_date': '27/04/2024'}

    Raises:
        Exception: For any unexpected errors during date retrieval.
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    return {
        "current_date": current_date
    }