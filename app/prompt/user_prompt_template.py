from string import Template
import json

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