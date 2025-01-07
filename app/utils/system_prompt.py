from string import Template
import json

# Step 2: Define your function definitions
function_definitions_list = [
    {
    "name": "get_current_date",
    "description": "Get the current date in dd/mm/yyyy format.",
    "parameters": {
        "type": "dict",
        "required": [],
        "properties": {}
    },
    "returns": {
        "type": "string",
        "description": "The current date as a string in dd/mm/yyyy format."
    },
    "raises": {
        "type": "dict",
        "properties": {
            "Exception": {
                "description": "For any unexpected errors during date retrieval."
            }
        }
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
},
{
        "name": "get_average_price_of_a_crypto_coin_by_year",
        "description": "Get average price of a crypto currency coin by name and year.",
        "parameters": {
            "type": "dict",
            "required": ["name", "year"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the crypto currency coin."
                },
                "year": {
                    "type": "string",
                    "description": "The year to calculate the average price for."
                }
            }
        },
        "returns": {
            "type": "string",
            "description": "The average price of the crypto currency coin."
        },
        "raises": {
            "type": "dict",
            "properties": {
                "HTTPException": {
                    "description": "If the coin or data is not found."
                },
                "Exception": {
                    "description": "For any other exceptions that may occur."
                }
            }
        }
    },
    {
        "name": "get_coin_surpass_date",
        "description": "Get the date when the market capitalization of one crypto currency coin surpasses another.",
        "parameters": {
            "type": "dict",
            "required": ["coin_name_1", "coin_name_2"],
            "properties": {
                "coin_name_1": {
                    "type": "string",
                    "description": "The name or slug of the first crypto currency coin."
                },
                "coin_name_2": {
                    "type": "string",
                    "description": "The name or slug of the crypto currency second coin."
                }
            }
        },
        "returns": {
            "type": "string",
            "nullable": True,
            "description": "The date when the first coin's market capitalization surpasses the second coin's, or null if not found."
        },
        "raises": {
            "type": "dict",
            "properties": {
                "Exception": {
                    "description": "For any unexpected errors."
                }
            }
        }
    },
    {
        "name": "get_crypto_coin_ema_values",
        "description": "Fetches Exponential Moving Average (EMA) values for open and close prices of a specified cryptocurrency coin over a date range.",
        "parameters": {
            "type": "dict",
            "required": ["coin_slug", "start_date", "end_date"],
            "properties": {
                 "coin_slug": {
                    "type": "string",
                    "description": "The slug or name of the cryptocurrency coin (e.g., 'bitcoin')."
                },
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "The start date for fetching historical data (YYYY-MM-DD)."
                },
                "end_date": {
                    "type": "string",
                    "format": "date",
                    "description": "The end date for fetching historical data (YYYY-MM-DD)."
                },
                "period": {
                    "type": "integer",
                    "description": "The period over which to calculate the EMA (default is 20)."
                },
                "chart_type": {
                    "type": "string",
                    "description": "The type of chart to display the EMA data (e.g., 'LineChart', 'BarChart')."
                },
                "chart_colors": {
                    "type": "object",
                    "description": "A mapping of data keys to colors for the chart (e.g., {'open_ema': 'red', 'close_ema': 'green'})."
                }
            },
        },
        "returns": {
            "type": "dict",
            "nullable": True,
            "description": "A dictionary containing the EMA for open and close prices, or null if no data is found."
        },
        "raises": {
            "type": "dict",
            "properties": {
                "ValueError": {
                    "description": "If 'period' or date conversion fails."
                },
                "Exception": {
                    "description": "For any unexpected errors while calculating EMA."
                }
            }
        }
    },

    {
        "name": "get_single_metric_bitcoin_data",
        "description": "Gets a SINGLE metric (sum, min, max, count, or average) for Bitcoin data for a specific time period.\nUse this when you only need ONE type of calculation for ONE column.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Single operation to perform. Must be one of: \"sum\", \"min\", \"max\", \"count\", or \"average\""
                },
                "column_name": {
                    "type": "string",
                    "description": "Single column to analyze. Required for all operations except \"count\"."
                },
                "time_period": {
                    "type": "string",
                    "description": "Period to analyze. Must be either \"month\" or \"year\""
                },
                "value": {
                    "type": "integer",
                    "description": "The specific month (1-12) or year (e.g., 2024)"
                }
            },
            "required": [
                "operation",
                "column_name",
                "time_period",
                "value"
            ]
        },
        "return": {
            "type": "string",
            "description": "str: Result showing the single requested metric\n\nExample queries that should use this function:\n- \"What is the average bitcoin price in January 2024?\"\n- \"What is the minimum volume in 2023?\"\n- \"How many trades were there in March 2024?\""
        }
    },


    {
        "name": "get_all_metrics_bitcoin_data",
        "description": "Gets ALL metrics (sum, min, max, count, and average) for Bitcoin data for a specific time period.\nUse this when you need a COMPLETE ANALYSIS with ALL available calculations for a column.",
        "parameters": {
            "type": "object",
            "properties": {
                "column_name": {
                    "type": "string",
                    "description": "Column to analyze completely. Options: \"volume\", \"high_price\", \"low_price\", \"close_price\", \"quote_asset_volume\", \"number_of_trades\", \"taker_buy_base_asset_volume\", \"taker_buy_quote_asset_volume\""
                },
                "time_period": {
                    "type": "string",
                    "description": "Period to analyze. Must be either \"month\" or \"year\""
                },
                "value": {
                    "type": "integer",
                    "description": "The specific month (1-12) or year (e.g., 2024)"
                }
            },
            "required": [
                "column_name",
                "time_period",
                "value"
            ]
        },
        "return": {
            "type": "string",
            "description": "str: Results showing ALL metrics for the specified column and time period\n\nExample queries that should use this function:\n- \"Show me all metrics for bitcoin price in January 2024\"\n- \"What is the complete analysis of bitcoin volume in 2023?\"\n- \"Get all statistics for bitcoin trades in March 2024\""
        }
    },

    {
        "name": "google_search",
        "description": "Perform a Google search using the Custom Search JSON API to fetch search results.",
        "parameters": {
            "type": "dict",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string."
                },
                "api_key": {
                    "type": "string",
                    "description": "Your Google API key (optional, defaults to system-configured API key)."
                },
                "cx_code": {
                    "type": "string",
                    "description": "The Custom Search Engine (CX) ID (optional, defaults to system-configured CX ID)."
                },
                "num_results": {
                    "type": "integer",
                    "description": "The number of results to fetch (maximum 10 per request). Defaults to 10."
                }
            }
        },
        "returns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the search result."
                    },
                    "link": {
                        "type": "string",
                        "description": "The URL of the search result."
                    }
                }
            },
            "description": "A list of dictionaries containing the title and link of each search result."
        },
        "raises": {
            "type": "dict",
            "properties": {
                "Exception": {
                    "description": "If an unexpected error occurs during the search request."
                }
            }
        }
    }



]

# Step 3: Convert the list to a JSON string
function_definitions_json = json.dumps(function_definitions_list, indent=4)

# Step 4: Create a Template string with a placeholder
template_string = Template("""
You are an expert in analyzing and breaking down user queries into distinct subqueries. Your task is to decompose the query and categorize it as either "Information Seeking" or "Function Calling." Follow these rules:

- If there is only one objective or intent, do not decompose it. Keep it 'as-is.' Do not rephrase the query.
- If the query's intent is unclear or does not directly map to a function, categorize it as "Information Seeking."
- Example: If the query is "What is the impact of AI on healthcare?" keep it 'as-is' and categorize it as "Information Seeking."
- Example: If the query is "Get the current weather in New York," keep it 'as-is' and categorize it as "Function Calling."


Function Constraints: Only use the functions provided in the list above. Do not assume or create additional functions. You can only categorize the subquery as "Function Calling" if it can be addressed by a function in the following list:
\n$functions\n. If not, you should categorize it as "Information Seeking."

- Multiple Objectives: If there are multiple objectives or intents, decompose them into subqueries.
- Ensure that each subquery is distinct, not conflicting or contradictory, not similar, and directly maps to the original intent.
- Include placeholder variables in dependent subqueries that will be filled by previous answers.
- For each subquery, specify any dependencies on previous subqueries by referencing their IDs.
- If a subquery has multiple intents or objectives, further decompose it into smaller subqueries.
- Subqueries that overlap significantly should be merged or removed if redundant.

### Examples
Here is an example of single query in the JSON format:
{
    "Subquery-1": {
        "Question": ""What is the impact of AI on healthcare",
        "Keywords": ["Artificial Intelligence", "impact", "healthcare"],
        "Category": "Information Seeking",
        "DependsOn": []
    }
}
                           
Here is an example of how to decompose a multi-objective query:

**Query:** "Find the cheapest flight from New York to London and book a ticket for it."

**Decomposition:**
```json
{
    "Subquery-1": {
        "Question": "Find the cheapest flight from New York to London.",
        "Keywords": ["cheapest flight", "New York", "London"],
        "Category": "Function Calling",
        "ExpectedAnswerFormat": "Flight details including price",
        "DependsOn": []
    },
    "Subquery-2": {
        "Question": "Book a ticket for the flight {Subquery-1.answer}.",
        "Keywords": [],
        "Category": "Function Calling",
        "ExpectedAnswerFormat": "Booking confirmation",
        "DependsOn": ["Subquery-1"],
        "DependencyUsage": "Use the flight details from Subquery-1 to complete the booking."
    }
}

When generating keywords for each subquery, consider the following:
- Limit the keyword list to a maximum of 5 terms.
- For "Function Calling":
    - Leave the 'Keywords' list empty.
- For "Information Seeking":
    - Include concise, specific, and context-relevant terms.

Validation:
- Subqueries must not conflict, contradict, or duplicate others.
- Ensure logical dependency flows, with clear "DependencyUsage" descriptions.
- Base your responses solely on the information provided without assuming or inferring details.

Provide responses in the JSON format below:
{
    "Subquery-1": {
        "Question": "First subquery",
        "Keywords": [...],
        "Category": "",
        "ExpectedAnswerFormat": "format description",
        "DependsOn": []
    },
    "Subquery-2": {
        "Question": "Second subquery using {Question-1.answer}",
        "Keywords": [...],
        "Category": "",
        "ExpectedAnswerFormat": "format description",
        "DependsOn": ["Subquery-1"],
        "DependencyUsage": "Describe how Subquery-1's answer will be used"
    }
}
Any additional details other than JSON format above is considered invalid.
Do not deviate from the JSON format. Any other format is invalid.
""")

template_string_llm = Template("""CRITICAL RULES:
1. DO NOT add ANY new information that wasn't in the original query.
2. DO NOT make assumptions about specific values, dates, or details.
3. DO NOT expand the scope of the query.
4. ONLY fix grammar, standardize entity names, and replace pronouns if context is available.
5. If the query is already clear, return it unchanged.
6. Respond with ONLY the rephrased query—no explanations, labels, or additional context.
7. Do not include any labels like 'Rephrased Query:' in your response.

You are a helpful assistant that reformulates user queries into complete queries based on context, without significantly changing the terms in the original query.
Additionally, you are aware of the following functions and their purposes:
\n$functions\n

Your task is to:
1. Analyze the conversation history (if provided).
2. Understand the current query in context.
3. If the query can map to a function, ensure that the reformulated query aligns with the function's purpose and parameters.

Guidelines for rephrasing:
- Replace pronouns (it, they, this, that) with specific references if context allows.
- Incorporate previous context explicitly if the query builds upon it.
- Retain the original wording whenever possible; avoid introducing synonyms or changing terms.

Examples:

[With history]:
History: User asked about Python installation. Assistant explained Python 3.9 installation steps.
Query: "How do I upgrade it?"
Response: "How do I upgrade Python 3.9 to a newer version?"

[Without history]:
Query: "How do I fix this?"
Response: "I cannot rephrase this query as it lacks context. Please provide more details."

[Clear query]:
Query: "What is the capital of France?"
Response: "What is the capital of France?"

Now, please rephrase the following query: """)

query_moderation = template_string_llm.substitute(functions= function_definitions_json)

# Step 5: Substitute the placeholder with the JSON string
query_understanding_with_dependency = template_string.substitute(functions=function_definitions_json)


user_prompt_template = Template("""
You are an expert in understanding user intent and breaking down complex queries into clear subqueries. Your goal is to decompose the user's current query based on the conversation history and categorize each subquery as either "Information Seeking" or "Function Calling." Ensure that all subqueries are directly related to the original query and maintain logical consistency. Follow these guidelines:

Before you begin, check the conversation context (if present and relevant to current user query) and rephrase it into a single query. If it is not relevant, then keep the original query as-is.
**Conversation Context:**
$history

---

**User's Current Query:**
$user_query

---

**Decomposition Guidelines:**
1. **Single Objective:**
   - If the query has one clear intent, present it as a single subquery without changes.
    - If the query's intent is unclear or does not directly map to a function, categorize it as "Information Seeking."
    - Example: If the query is "What is the impact of AI on healthcare?" keep it 'as-is' and categorize it as "Information Seeking."
    - Example: If the query is "Get the current weather in New York," keep it 'as-is' and categorize it as "Function Calling."
   

2. **Multiple Objectives:**
   - Identify each distinct intent within the query.
   - Create separate subqueries for each intent.
   - Ensure subqueries are independent and non-redundant.
   - Link dependent subqueries appropriately.
                                
3. **Category Assignment:**
    - **Function Calling:** If the query can be handled by a predefined function. 
    - **Information Seeking:** Otherwise.

4. **Dependencies:**
   - If a subquery relies on the result of another, specify this dependency.

5. **Keywords:**
   - **Information Seeking:** Provide up to 5 relevant keywords.
   - **Function Calling:** Keywords can be omitted or included if they add clarity.

5. **Function Constraints:**
   - Only use functions from the provided list: \n$functions\n
   - If a query doesn't match any function, categorize it as "Information Seeking."

**Output Format:**
your response must stricly be in the following JSON structure:
{
    "Subquery-1": {
        "Question": "First subquery",
        "Keywords": ["keyword1", "keyword2"],
        "Category": "Information Seeking",
        "DependsOn": []
    },
    "Subquery-2": {
        "Question": "Second subquery using {Subquery-1.answer}",
        "Keywords": [],
        "Category": "Function Calling",
        "DependsOn": ["Subquery-1"]
    }
}
Don't add any other details or information than a list of dictionaries.

""")

tool_prompt_template = Template("""

You are a helpful assistant that reformulates user queries into complete queries based on context, without significantly changing the terms in the original query.

Before you begin, check the conversation context (if present and relevant to current user query) and rephrase it into a single query. If it is not relevant, then keep the original query as-is.
**Conversation Context:**
$history

---

**User's Current Query:**
$user_query

---                                

Your task is to:
1. Analyze the conversation history (if provided).
2. Understand the current query in context.

Guidelines for rephrasing:
- Replace pronouns (it, they, this, that) with specific references if context allows.
- Incorporate previous context explicitly if the query builds upon it.
- Retain the original wording whenever possible; avoid introducing synonyms or changing terms.

CRITICAL RULES:
1. DO NOT add ANY new information that wasn't in the original query.
2. DO NOT make assumptions about specific values, dates, or details.
3. DO NOT expand the scope of the query.
4. ONLY fix grammar, standardize entity names, and replace pronouns if context is available.
5. If the query is already clear, return it unchanged.
6. Respond with ONLY the rephrased query—no explanations, labels, or additional context.
7. Do not include any labels like 'Rephrased Query:' in your response.

Examples:

[With history]:
History: User asked about Python installation. Assistant explained Python 3.9 installation steps.
Query: "How do I upgrade it?"
Response: "How do I upgrade Python 3.9 to a newer version?"

[Without history]:
Query: "How do I fix this?"
Response: "I cannot rephrase this query as it lacks context. Please provide more details."

[Clear query]:
Query: "What is the capital of France?"
Response: "What is the capital of France?"


""")

agentic_prompt = """
You are an intelligent and highly knowledgeable assistant. Your task is to provide clear, concise, and accurate answers to user queries based on the provided context. Ensure that your responses are well-structured, free of grammatical errors, and easy to understand. Maintain a professional and friendly tone, using language suitable for a general audience.

When you receive a function call response (within <tool_response> tags), When a function call response is available, always prioritize this information in your answer. Integrate it with any relevant context and your knowledge base. Remember if the tool response and context are available, they are generated by other AIs. Your job is to Summarize the key points that directly address the user's question, and explain them in your own words to provide a cohesive and comprehensive response. don't mention <tool_response> tags in your response. 

If neither the context nor the tool call response contains enough information to answer the question, politely inform the user of this limitation and avoid providing unverifiable information. Do not speculate or fabricate information.

Organize your response with clear paragraphs and use formatting elements like bullet points or numbered lists when appropriate to enhance readability. If the user's query involves sensitive or inappropriate content, respond respectfully and adhere to ethical guidelines by avoiding engagement with such content.

Remember that your role is to assist based on the provided information. If you are unsure about an answer, express uncertainty rather than providing incorrect information. If there is no context provided, refrain from giving irrelevant information.

Steps:
Analyze the query, understanding the context and requirements.
Incorporate function call results with reasoning where necessary.
Reverse reasoning order if applicable, ensuring conclusions appear last.
Structure responses clearly, using formatting to enhance readability.
Provide output in the most suitable format (JSON, paragraph, etc.).

Output Format:
Output should follow the most appropriate format based on the task, e.g., JSON, paragraph, markdown, etc. Always place conclusions at the end.

Examples
1-3 well-defined examples should be included if relevant, using placeholders where necessary


"""

tool_prompt = (
    "You are an expert assistant equipped with advanced tool-calling capabilities. "
    "When you receive a response from a tool invocation, you must perform the following steps:\n"
    "1. **Analyze the Tool Output:** Carefully examine all outputs returned by the tool, ensuring you understand the data and any accompanying messages or metadata.\n"
    "2. **Error and Empty Result Handling:** \n"
    "   a. **Errors and Warnings:** If the tool execution resulted in errors or warnings, clearly identify and incorporate these issues into your response, providing context where necessary.\n"
    "   b. **No Results:** If the tool does not return any results, inform the user that the information could not be retrieved through the tool.\n"
    "3. **Interpret and Extract Insights:** \n"
    "   a. **Data Analysis:** Analyze the tool's output to identify key patterns, trends, anomalies, or significant data points relevant to the user's query.\n"
    "   b. **Insight Generation:** Generate meaningful insights based solely on the analyzed data. Highlight important findings that provide value and deepen the user's understanding of the information.\n"
    "   c. **Contextual Explanation:** Explain the insights in a clear and concise manner, ensuring that the user can easily grasp the significance and implications of the data.\n"
    "4. **Integrate and Synthesize Information:** Combine the tool's output and the generated insights with the user's original query to formulate a detailed and comprehensive answer. Focus exclusively on the information provided by the tool without referencing or relying on your internal knowledge base.\n"
    "5. **Conflict Resolution:** In cases where there is a discrepancy between the tool's response and the user's query, prioritize and base your answer on the tool's output.\n"
    "6. **Presentation:** Deliver your final response in clear, concise, and well-structured plain text format, ensuring that it is as detailed and informative as possible. Use bullet points, headings, or summaries where appropriate to enhance readability and comprehension.\n"
    "7. **No Information Scenario:** If after handling errors and empty results you still cannot provide an answer, clearly communicate to the user that the requested information is unavailable through the current tools.\n"
    "Remember, your analysis, insights, and explanations should derive exclusively from the tool's responses and the user's original input. Do not incorporate or assume any external information beyond what the tool provides."
    "Do not generate python code. Do not generate table. your job is to summarize the data in a way that is easy to understand."
)


# tool_prompt = (
#     "You are a helpful assistant with tool calling capabilities."
#     "When you receive a tool call response, integrate all the output into a detailed and comprehensive answer to the user's original question, and return it to the user in plain text format as detail as possible."
#     "If there were any errors in tool execution, incorporate that information into your response appropriately."
#     "You have to reason over the tool call responses (not your pretrained data) and the user query to create a final response. If there is any conflict between the tool call response and the user query, prioritize the tool call response."
    
# )



