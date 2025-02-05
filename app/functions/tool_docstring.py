import datetime

# Example usage:
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

def get_current_date():
    """
    Get current date.
    
    Input format:
    {
        "name": "string",
        "parameters": {}
    }
    """
    return datetime.datetime.now().strftime("%Y-%m-%d")