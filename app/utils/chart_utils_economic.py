# app/utils/chart_generator.py

import logging
import re  # For parsing 'total_value'
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)

# Define chart configurations for the two specific query types
CHART_CONFIG_MAP = {
    "total_fdi_value_by_country": {
        "chart_type": "BarChart",
        "x_key": "country",
        "x_axis_label": "Country",
        "y_axis_label": "Total FDI Value (Millions USD)",
        "series": [
            {"dataKey": "total_value", "color": "#82ca9d", "name": "Total FDI Value"}
        ],
        "chart_title": "Total FDI Value by Country",
    },
    "total_fdi_value_by_sector": {
        "chart_type": "PieChart",
        "pie_data_key": "total_value",
        "name_key": "sector",
        "x_key": "sector",  # Added to prevent NoneType
        "x_axis_label": "Sector",  # Optional
        "y_axis_label": "Total FDI Value (Millions USD)",  # Optional
        "series": [
            {"dataKey": "total_value", "color": "#8884d8", "name": "Total FDI Value"}
        ],
        "chart_title": "Total FDI Value by Sector",
    },
}

def parse_total_value(value_str: str) -> float:
    """
    Parses the 'total_value' string and extracts the numerical value.
    Example: '3000.97 Millions USD' -> 3000.97
    """
    try:
        match = re.match(r"([\d.,]+)", value_str)
        if match:
            number_str = match.group(1).replace(',', '')
            return float(number_str)
        else:
            logger.warning(f"Unable to parse total_value: {value_str}")
            return 0.0
    except Exception as e:
        logger.error(f"Error parsing total_value '{value_str}': {e}")
        return 0.0

async def generate_chart_config(
    query_type: str,
    query_result: Any,
    chart_type: Optional[str] = None,
    chart_colors: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Generates a chart configuration based on the query type and result data.
    
    Args:
        query_type (str): The type of query executed. Supported types:
            - "total_fdi_value_by_country"
            - "total_fdi_value_by_sector"
        query_result (Any): The result data from the query.
        chart_type (Optional[str]): Override the default chart type if provided.
        chart_colors (Optional[Dict[str, str]]): Custom colors for the chart series.
    
    Returns:
        Optional[Dict[str, Any]]: The chart configuration dictionary or None if an error occurs.
    
    Raises:
        ValueError: If the query_type is unsupported.
        TypeError: If chart_colors is not a dictionary.
    """
    if chart_colors is None:
        chart_colors = {}

    if not isinstance(chart_colors, dict):
        logger.error(f"chart_colors must be a dictionary, got {type(chart_colors).__name__}")
        raise TypeError(f"chart_colors must be a dictionary, got {type(chart_colors).__name__}")

    config_template = CHART_CONFIG_MAP.get(query_type)
    logger.info(f"config_template: {config_template}")
    if not config_template:
        logger.error(f"Unsupported query_type: {query_type}")
        raise ValueError(f"Unsupported query_type: {query_type}")

    try:
        chart_type_final = chart_type if chart_type else config_template["chart_type"]
        chart_title = config_template.get("chart_title", "")
        x_key = config_template.get("x_key")
        x_axis_label = config_template.get("x_axis_label", "")
        y_axis_label = config_template.get("y_axis_label", "")
        series_config = config_template.get("series", [])

        # Initialize empty data
        data: List[Dict[str, Any]] = []

        # Process query_result based on query_type
        if query_type == "total_fdi_value_by_country":
            data = [
                {
                    "country": entry["country"],
                    "total_value": parse_total_value(entry["total_value"])
                }
                for entry in query_result
            ]
            print(f"data1: {data}")

        elif query_type == "total_fdi_value_by_sector":
            data = [
                {
                    "sector": entry["sector"],
                    "total_value": parse_total_value(entry["total_value"])
                }
                for entry in query_result
            ]

        else:
            # This block should not be reached due to earlier validation
            logger.error(f"Unsupported query_type during processing: {query_type}")
            raise ValueError(f"Unsupported query_type: {query_type}")

        # Apply custom colors if provided
        for series in series_config:
            if series["dataKey"] in chart_colors:
                series["color"] = chart_colors[series["dataKey"]]

        # Determine tooltip formatter types based on available keys
        tooltip_formatter = "usd" if any("fdi_value" in series["dataKey"] for series in series_config) else None
        tooltip_label_formatter = "date_us_format" if x_key and "date" in x_key else None

        # Determine Y-axis Tick Formatter Type
        yAxisTickFormatterType = "shortNumber" if any("fdi_value" in series["dataKey"] for series in series_config) else None

        print(f"data: {data}")
        # Build the chart_config dictionary
        chart_config = {
            "chartType": chart_type_final,
            "data": data,
            "config": {
                "xKey": x_key,
                "xAxisLabel": x_axis_label,
                "yAxisLabel": y_axis_label,
                "yAxis": {
                    "label": {
                        "value": y_axis_label,
                        "angle": -90,
                        "position": "insideLeft",
                        "offset": -60,
                        "dy": 10,
                    },
                    "tick": {
                        "fontSize": 12
                    },
                    "padding": {
                        "top": 10,
                        "bottom": 10
                    }
                },
                "series": series_config,
                "dataPointCount": len(data),
                "tooltipFormatterType": tooltip_formatter,
                "tooltipLabelFormatterType": tooltip_label_formatter,
                "yAxisTickFormatterType": yAxisTickFormatterType,  # Added formatter type
                "margin": { "top": 20, "right": 30, "left": 60, "bottom": 60 },  # Adjusted left margin
            },
            "chartTitle": chart_title,
            "rawData": query_result,
        }

        # Add camelCase keys for PieChart
        if chart_type_final == "PieChart":
            chart_config["config"]["pieDataKey"] = config_template.get("pie_data_key")
            chart_config["config"]["nameKey"] = config_template.get("name_key")

        return chart_config

    except Exception as e:
        logger.error(f"Error in generate_chart_config ({query_type}): {e}")
        return None
