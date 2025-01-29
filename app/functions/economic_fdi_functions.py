import logging, json
from enum import Enum
from typing import Union, Optional, Dict, Any, List, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session  # Assuming the session setup is already in app.db.session
from app.crud.economic_fdi import *  # Importing CRUD functions for economic data
from app.functions.tool_interface import Tool
from app.utils.chart_utils_economic import generate_chart_config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define allowed parameters for each query_type
ALLOWED_PARAMETERS = {
    "trends_in_fdi_value": {"start_year", "end_year", "countries"},
    "total_fdi_value_by_country": {"start_year", "end_year"},
    "total_fdi_value_by_sector": set(),  # No parameters allowed
}

def extract_years(query_type, arguments):
    """
    Extracts start_year and end_year from arguments for 'total_fdi_value_by_country' queries.

    Args:
        arguments: A dictionary containing query information.

    Returns:
        A dictionary containing 'start_year' and 'end_year', or None if the query type is incorrect or years are missing.
        Returns a string explaining error if input is not a dictionary.
    """

    if not isinstance(arguments, dict):
      return "Error: Input must be a dictionary"
    
    if query_type == 'total_fdi_value_by_country':
        

        start_year = arguments.get('start_year')
        end_year = arguments.get('end_year')

        if start_year and end_year: #check if both are not None
          return {'start_year': start_year, 'end_year': end_year}
        else:
          return None  # Return None if either year is missing
    elif query_type == 'trends_in_fdi_value':
        # Create a copy to avoid modifying the original dictionary
        filtered_arguments = arguments.copy()
        filtered_arguments.pop('chart_type', None)  # Remove 'chart_type' if it exists. None prevents KeyError
        return filtered_arguments
    else:
        filtered_arguments = arguments.copy()
        filtered_arguments.pop('chart_type', None)  # Remove 'chart_type' if it exists. None prevents KeyError
        return filtered_arguments # Return None if the query type is not a match

    
async def get_query_economic_data(
    query_type: str,
    parameters: Optional[Dict[str, Any]] = None,
    chart_type: Optional[str] = "BarChart"
) -> Union[Dict[str, Any], float, Dict[str, Any], None]:
    """
    Retrieve FDI (Foreign Direct Investment) economic data in Indonesia, offering various insights based on the specified query type.

    Args:
        query_type: The type of FDI data query to perform. Supported options are:
            - **"trends_in_fdi_value"**: Analyze trends in FDI across different countries and year ranges.
            - **"total_fdi_value_by_country"**: Calculate the total FDI by country within a specified year range.
            - **"total_fdi_value_by_sector"**: Determine the total FDI by sector.

        parameters: Additional parameters required for the selected `query_type`. Do not generate parameters more than required. The required parameters vary based on the `query_type` as detailed below:

            **1. "trends_in_fdi_value"**
                - `start_year` (int, optional): The starting year for the FDI trend analysis. Defaults to **2010**.
                - `end_year` (int, optional): The ending year for the FDI trend analysis. Defaults to **2023**.
                - `countries` (List[str], optional): A list of countries to include in the analysis. Defaults to `['Singapore', 'Malaysia', 'Brunei Darussalam', 'Cambodia', 'Laos', 'Myanmar', 'Thailand', 'Philippines', 'Vietnam']`. Supported countries are:
                    - Brunei Darussalam
                    - Cambodia
                    - Laos
                    - Malaysia
                    - Myanmar
                    - Singapore
                    - Thailand
                    - Philippines
                    - Vietnam

            **2. "total_fdi_value_by_country"**
                - `start_year` (int, optional): The starting year for calculating total FDI by country. Defaults to **2010**.
                - `end_year` (int, optional): The ending year for calculating total FDI by country. Defaults to **2023**.

            **3. "total_fdi_value_by_sector"**
                - *No additional parameters required.*
        chart_type: The type of chart to display. Defaults to "BarChart".

    Returns:
        Union[List[Dict[str, Any]], float, None]:
            - **"trends_in_fdi_value"**: Returns a list of dictionaries containing `sector`, `country`, `year`, and `total_value`.
            - **"total_fdi_value_by_country"**: Returns a list of dictionaries with `country` and `total_value`.
            - **"total_fdi_value_by_sector"**: Returns a list of dictionaries with `sector` and `total_value`.
            - Returns `None` if an unsupported `query_type` is provided.

    Raises:
        ValueError: If an unsupported `query_type` is specified.
        KeyError: If required parameters for the specified `query_type` are missing.


    """
    
    parameters = parameters or {}

     

    # Define supported query types
    supported_query_types = {
        "trends_in_fdi_value",
        "total_fdi_value_by_country",
        "total_fdi_value_by_sector",
    }

    if query_type not in supported_query_types:
        logger.error(f"Unsupported query_type: {query_type}")
        raise ValueError(f"Unsupported query_type: {query_type}")
    

    logger.info(f"parameters: {parameters}")
    parameters = extract_years(query_type, parameters)


    async with get_session(db_identifier) as db:
        try:
            

            # Ensure 'countries' is a list if it exists
            if 'countries' in parameters and isinstance(parameters['countries'], str):
                try:
                    parameters['countries'] = json.loads(parameters['countries'].replace("'", "\""))
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse 'countries': {parameters['countries']}")
                    raise ValueError("'countries' parameter must be a JSON-serializable list.")
            # Initialize EconomicTool with the current database session and parameters
            economic_tool = EconomicTool(db, query_type, parameters)
            query_result = await economic_tool.execute()
            logger.info(f"query_result_1: {query_result}")

            if query_result is None:
                logger.warning(f"No data returned for query_type: {query_type}")
                return None

            # Define which query_types are visualizable
            visualizable_queries = {
                "total_fdi_value_by_country",
                 "total_fdi_value_by_sector"
            }
            if query_type in visualizable_queries:
                # Generate chart configuration
                chart_config = await generate_chart_config(
                    query_type=query_type,
                    query_result=query_result,
                    chart_type=chart_type,
                )
                return chart_config
            else:
                logger.info(f"query_result : {query_result}")
                return query_result
        except ValueError as ve:
            logger.error(f"ValueError in get_query_economic_data: {ve}")
            return None
        except TypeError as te:
            logger.error(f"TypeError in get_query_economic_data: {te}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_query_economic_data: {e}")
            return None


class EconomicTool(Tool):
    """
    A tool to execute various economic-related queries based on the query_type.
    """

    
    # Mapping of query_type to corresponding query function
    QUERY_FUNCTION_MAP: Dict[str, Callable[..., Any]] = {
        "trends_in_fdi_value": trends_in_fdi_value,
       
        "total_fdi_value_by_country": total_fdi_value_by_country,
        "total_fdi_value_by_sector": total_fdi_value_by_sector,
        # Add other query mappings here
    }

    def __init__(
        self, 
        db_session: AsyncSession, 
        query_type: str, 
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Initializes the EconomicTool with the necessary parameters.

        Args:
            db_session (AsyncSession): The database session to use for queries.
            query_type (str): The type of economic data query to perform.
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
            # Pass parameters to query functions where applicable
            if self.parameters:
                return await query_func(self.db_session, **self.parameters)
            else:
                return await query_func(self.db_session)
        except Exception as e:
            logger.error(f"Error executing query '{self.query_type}': {e}")
            raise
