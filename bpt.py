import inspect
from app.utils.message_utils import get_query_economic_data as get_query

def get_query_economic_data(input_data):
    """
    Get economic data based on query parameters.
    
    Input format:
    {
        "name": "string",
        "parameters": {
            "query_type": "string (total_fdi_value_by_sector, total_fdi_value_by_country)",
            "start_year": "string",
            "end_year": "string",
            "countries": "list"
        },
        "chart_type": "string (BarChart, LineChart, PieChart)"
    }
    """
    pass
response = inspect.getdoc(get_query_economic_data)

print(response)

response1 = inspect.getdoc(get_query)

print(response1)