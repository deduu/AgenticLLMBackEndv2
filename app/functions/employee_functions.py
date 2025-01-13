# main.py

import logging
from typing import Literal, Union, Optional, Dict, Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.pertamina_employee import EmployeeData 
from app.db.session import setup_database_session, get_session  # Assuming the new code is in app/database.py
from app.crud.employee import *
from app.functions.tool_interface import Tool
logger = logging.getLogger(__name__)


from typing import Union, Optional, Dict, Any

async def get_query_employee_data(
    query_type: str,
) -> Union[Dict[str, Any], float, Dict[str, Any], None]:
    """
    Get employee data, providing various insights based on the specified query type.

    Args:
        query_type: The type of employee data query to perform. Options are:
            - "average_age": Compute average age of employees.
            - "average_length_of_service": Compute average length of service.
            - "average_distance_from_home": Compute average distance from home.
            - "average_salary_hike_from_last_year": Compute average salary hike from last year.
            - "retirement_rate": Compute the retirement rate.
            - "engagement_rate": Compute the engagement rate.
            - "satisfaction_rate": Compute the satisfaction rate.

    Returns:
        dict: 
              Returns a float or dict for scalar or composite queries, or None if an error occurs.

    """

    # Define supported query types
    supported_query_types = {
        "average_age",
        "average_length_of_service",
        "average_distance_from_home",
        "average_salary_hike_from_last_year",
        "retirement_rate",
        "engagement_rate",
        "satisfaction_rate",
        # Add more query types as needed
    }

    if query_type not in supported_query_types:
        logger.error(f"Unsupported query_type: {query_type}")
        raise ValueError(f"Unsupported query_type: {query_type}")

    async with get_session(db_identifier) as db:
        try:
            # Initialize EmployeeTool with the current database session, query_type, and parameters
            employee_tool = EmployeeTool(db, query_type)
            query_result = await employee_tool.execute()

            if query_result is None:
                logger.warning(f"No data returned for query_type: {query_type}")
                return None

            else:
                logger.info(f"query_result : {query_result}")
             
                return query_result
        except ValueError as ve:
            logger.error(f"ValueError in get_query_employee_data: {ve}")
            return None
        except TypeError as te:
            logger.error(f"TypeError in get_query_employee_data: {te}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_query_employee_data: {e}")
            return None
        


class EmployeeTool(Tool):
    """
    A tool to execute various employee-related queries based on the query_type.
    """

    # Mapping of query_type to corresponding query function
    QUERY_FUNCTION_MAP: Dict[str, Callable[..., Any]] = {
        "average_age": average_age, 
        "average_length_of_service": average_length_of_service,
        "average_distance_from_home": average_distance_from_home,
        "average_salary_hike_since_last_year": average_salary_hike_since_last_year,
        "retirement_rate": retirement_rate,
        "engagement_rate": engagement_rate,
        "satisfaction_rate": satisfaction_rate, 
        # Map other query_types to their functions
    }

    def __init__(
        self, 
        db_session: Any, 
        query_type: str, 
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initializes the EmployeeTool with the necessary parameters.

        Args:
            db_session (AsyncSession): The database session to use for queries.
            query_type (str): The type of employee data query to perform.
            parameters (dict, optional): Additional parameters for specific queries.
        """
        self.query_type = query_type
        self.parameters = parameters or {}
        self.db_session = db_session

    async def execute(self) -> Any:
        """
        Executes the query based on the query_type and returns the result.

        Returns:
            Any: The result of the executed query.
        
        Raises:
            ValueError: If the query_type is unsupported.
        """
        query_func = self.QUERY_FUNCTION_MAP.get(self.query_type)
        if not query_func:
            logger.error(f"Unsupported query_type: {self.query_type}")
            raise ValueError(f"Unsupported query_type: {self.query_type}")
        
        try:
            if self.query_type == "average_metrics":
                return await query_func(self.db_session)
            # Handle other query types with parameters if necessary
            else:
                return await query_func(self.db_session)
        except Exception as e:
            logger.error(f"Error executing query '{self.query_type}': {e}")
            raise

