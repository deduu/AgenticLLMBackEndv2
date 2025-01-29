function_definitions_json = [
    {
    "name": "get_current_date",
    "description": "Get the current date in dd/mm/yyyy format.",
    "parameters": {
        "type": "dict",
        "required": [],
        "properties": {}
    }
},
{
    "name": "query_sales_data",
    "description": "Get sales data, providing various insights based on the specified query type.",
    "parameters": {
        "type": "object",
        "required": ["query_type","parameters","chart_type"],
        "properties": {
            "query_type": {
                "type": "string",
                "description": "The type of sales data query to perform. Supported types: sales_by_market, sales_by_agent, clients_by_industry, segment_of_enterprise, total_sales_over_time, top_customers_by_sales, average_sales_per_order, sales_in_date_range, sales_by_product_code."
            },
            "parameters": {
                "type": "object",
                "description": "Additional parameters required for the specific query type.",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "The year for which to filter the data (e.g., 2023). Applicable for certain queries."
                    },
                    "month": {
                        "type": "integer",
                        "description": "The month for which to filter the data (1-12). Applicable for certain queries."
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "The number of top records to retrieve. Applicable for top customers query."
                    },
                    "start_date": {
                        "type": "string",
                        "description": "The start date for the sales range in YYYY-MM-DD format. Applicable for date range queries."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "The end date for the sales range in YYYY-MM-DD format. Applicable for date range queries."
                    },
                },
                "required": []
            },
            "chart_type": {
                "type": "string",
                "description": "The type of chart to display (e.g., 'LineChart', 'BarChart'). Defaults to 'LineChart'."
            }
        },
       
    }
}
]