import logging
import pytest
from app.crud.employee import initialize_employee_database_sessions
from app.functions.employee_functions import get_query_employee_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_query_sales_data():
    await initialize_employee_database_sessions()
    result = await get_query_employee_data("average_age")
    logger.info(f"Result: {result}")
    assert result is not None
