import logging
import pytest
from app.crud.employee import initialize_employee_database_sessions
from app.functions.employee_functions import get_query_employee_data
from app.crud.economic_fdi import initialize_fdi_database_sessions
from app.functions.economic_fdi_functions import get_query_economic_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# @pytest.mark.asyncio
# async def test_query_sales_data():
#     await initialize_employee_database_sessions()
#     result = await get_query_employee_data("average_age")
#     logger.info(f"Result: {result}")
#     assert result is not None

@pytest.mark.asyncio
async def test_query_sales_data():
    await initialize_fdi_database_sessions()

    # Use logger.info within get_query_economic_data
    result = await get_query_economic_data("trends_in_fdi_value")
    logger.info(f"Result from get_query_economic_data: {result}")

    assert result is not None
