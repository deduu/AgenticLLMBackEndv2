
import logging
import json
import re
import asyncio
from collections.abc import Iterable
# Simple topological sort based on dependencies
from collections import defaultdict, deque
from typing import Dict, Any, List

from app.schemas.message_types import LLMRequest
# from app.dependencies import model_pool
from app.services.message_preparer import MessagePreparer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Agentic:
    def __init__(self, small_llm=None, medium_llm =None, large_llm=None, rag=None, function_caller=None, max_hops=3, excel_loader=None, function_registry=None):
        self.small_llm = small_llm  # The LLM instance
        self.medium_llm = medium_llm  # The LLM instance
        self.large_llm = large_llm  # The LLM instance
        self.rag = rag  # The RAG instance
        self.function_caller = function_caller  # The function caller instance
        self.max_hops = max_hops  # Maximum number of hops for multi-hop reasoning
        self.is_model_loaded = False
        self.combined_response = {}
        self.context = {}
        self.excel_loader = excel_loader
        self.function_registry = function_registry
        self.message_preparer = MessagePreparer()
        logger.info(f"AgenticLLM is starting...")

    @classmethod
    def from_defaults(cls):
        # You can set default instances or None for llm, rag, and function_caller
        default_small_llm = None  # Replace with a default LLM instance if needed
        default_medium_llm = None  # Replace with a default LLM instance if needed
        default_large_llm = None  # Replace with a default LLM instance if needed
        default_rag = None  # Replace with a default RAG instance if needed
        default_function_caller = None  # Replace with a default function caller if needed
        defaut_excel_loader = None
        return cls(default_small_llm, default_medium_llm, default_large_llm, default_rag, default_function_caller, excel_loader=defaut_excel_loader)

    
    def load_llm_model(self, model_id, device=None):
        """
        Loads the selected LLM model.

        Parameters:
            model_id (str): The Hugging Face model ID to load.
            device (str): The device to run the model on ('cpu' or 'cuda').

        Returns:
            bool: True if model loaded successfully, False otherwise.
        """
        try:
            # self.llm = load_llm_model_cached(model_id=model_id, device=device)
          
            self.is_model_loaded = True
            # logger.info(f"Model {model_id} loaded successfully on {device}.")
            # Load any additional components that requires LLM tokenizer or model
            # if self.llm:
            #     self.load_excel_processor()
            return True
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            return False
    
    async def understand(self, message:LLMRequest):
        logger.info("Trying to understand ... ")
        logger.info(f"history_messages: {message.history_messages}")

        history_messages = await self.summarize_conversation(message)
        messages = self.message_preparer.prepare_query_for_message(message.query, system_prompt=message.system_prompt, history_messages=history_messages)
         # Get 'llamma_small' model instance
        # llm_small = await self.llm.get_model_by_type("llamma_small")
        # logger.info(f"llm_small: {llm_small}")
        subqueries = await self.medium_llm.generate(messages=messages, max_new_tokens=512)
        logger.info(f"Generated subqueries: {subqueries}")
        return subqueries
        subqueries = await self.llm.generate(
            messages=messages, max_new_tokens=512)
        
        

        return subqueries
    
    async def process(self, subqueries, message:LLMRequest):
        logger.info("Trying to process ... ")
        
        # Convert subqueries to dictionary if it's a string
        if isinstance(subqueries, str):
            import json
            subqueries = json.loads(subqueries)

        processing_order = self.message_preparer.determine_processing_order(subqueries)

        
        combined_response = {}

        # If there's only one item, process it
        if len(processing_order) == 1:
            subquery_id = processing_order[0]
            processed_result = await self._process_single_subquery(
                subquery_id, 
                subqueries[subquery_id], 
                combined_response,
                message.collections
            )
            combined_response[subquery_id] = processed_result
        else:
            # Otherwise, process all but the last item
            for subquery_id in processing_order[:-1]:  # Exclude the last one
                processed_result = await self._process_single_subquery(
                    subquery_id, 
                    subqueries[subquery_id], 
                    combined_response,
                    message.collections
                )
                combined_response[subquery_id] = processed_result

        return combined_response
    
    async def summarize_conversation(self, message:LLMRequest) -> str:
        
        summarization_prompt = "Summarize the following conversation history in a brief without losing any context in a paragraph no more than 250 words:\n\n"
        messages = self.message_preparer.prepare_query_for_summary(message.query, system_prompt=summarization_prompt, history_messages=message.history_messages)
        summarized_history = await self.small_llm.generate(messages=messages, max_new_tokens=512)
        logger.info(f"summarized_history: {summarized_history}")
        return summarized_history
    

    async def _process_single_subquery(self, subquery_id, subquery_data, combined_response, prefixes):
        """
        Process individual subquery with dependency handling
        """
        initial_subquery = subquery_data["Question"]
        keywords = subquery_data["Keywords"]
        initial_category = subquery_data["Category"]
        depends_on = subquery_data.get("DependsOn", [])
        expected_format = subquery_data.get("ExpectedAnswerFormat", "")
        dependency_usage = subquery_data.get("DependencyUsage", None)

        # Handle dependencies
        if depends_on:
            dependency_context = self._prepare_dependency_context(
                depends_on, 
                combined_response, 
            )
            # Process with dependency context
            result, category = await self._process_with_dependencies(
                initial_subquery, 
                dependency_context, 
                expected_format, 
                dependency_usage
            )

            return self._categorize_result(result, category)
        else:
            # Standard processing
            result, category = await self._standard_subquery_processing(
                initial_subquery, 
                keywords, 
                initial_category, 
                prefixes
            )
            return self._categorize_result(result, category)
    

    async def _standard_subquery_processing(self, subquery, keywords, initial_category, prefixes):
        """
        Standard subquery processing logic
        """
        result, resolved_category = await self.multi_hop_process(
            subquery=subquery,
            keywords=keywords,
            initial_category=initial_category,
            prefixes=prefixes
        )
        
        return result, resolved_category

    def _prepare_dependency_context(self, depends_on, combined_response):
        """
        Prepares the context from dependencies for the subquery
        """
        dependency_context = []

        for dep_id in depends_on:
            dep_data = combined_response.get(dep_id, {})
            source = dep_data.get("Source", "")
            if isinstance(source, list):
                # Extract text from each item
                texts = [item.get("text", "") for item in source]
                combined_text = "\n".join(texts)
                dependency_context.append(combined_text)
            else:
                dependency_context.append(source)

        logger.info(f"Dependency context: {dependency_context}")
        return dependency_context

    def _categorize_result(self, result, category):
        """
        Categorize and structure result based on processing category
        """
        if category == "Function Calling":
            return {
                "Source": result,
                "Type": "Action"
            }
        elif category in ["Information Seeking"]:
            return {
                "Source": result or "No Relevant document found",
                "Type": "RAG"
            }
        else:
            # Handle other categories or default case
            return {
                "Source": result,
                "Type": category
            }
        
    async def multi_hop_process(self, subquery, keywords, initial_category, prefixes):
        """
        Executes multi-hop reasoning for a subquery. If initial categorization fails,
        it applies a fallback mechanism after multi-hop reasoning fails.
        """

        # logger.info(f"multi_hop_process: {subquery} with keywords: {keywords} and initial_category: {initial_category} and context: {context}")
        hops = 0
        category = initial_category
        current_query = subquery
        result = None  # Initialize result outside the loop

        while hops < self.max_hops:
            try:
    
                
                result = await self.execute_subquery(current_query, keywords, category, prefixes=prefixes)
                # logger.info(f"Execute subquery Result: {result}")
                # logger.info(f"Current query: {current_query}")


                # Use LLM to judge if the result is valid and complete
                if await self.is_valid_result(result, current_query):
                    return result, category 

                # If the result is not complete, generate a follow-up subquery
                # logger.info(f"Incomplete result for subquery: '{current_query}', generating follow-up query.")
                # logger.info(f"result type: {type(result)}")
                # next_subquery = self.medium_llm.generate_followup_subquery(current_query, result)
                next_subquery = current_query
                logger.info(f"next_subquery: {next_subquery}")

                if next_subquery:
                    current_query = next_subquery
                    hops += 1
                else:
                    logger.info("No further subqueries generated. Exiting multi-hop reasoning.")
                    break

            except Exception as e:
                logger.error(f"Error encountered for subquery: '{current_query}', applying fallback. Error: {e}")
                break

        # Multi-hop reasoning failed: now attempt fallback (switch to function calling)
        logger.error(f"Multi-hop reasoning failed after {self.max_hops} hops for subquery: {subquery}")
        # return None, category
        # Switch category and retry with fallback mechanism
        # Multi-hop reasoning failed: now attempt fallback (switch to function calling)
        fallback_category = "Function Calling" if category == "Information Seeking" else "Information Seeking"
        logger.info(f"Applying fallback mechanism: Switching to {fallback_category}")

        try:
            result = await self.execute_subquery(current_query, keywords, fallback_category, prefixes=prefixes)

            logger.info(f"Result from execute: {result}")
            # Validate the result after fallback
            if await self.is_valid_result(result, subquery):
                return result, fallback_category  # Make sure you return both result and category
            else:
                if fallback_category == "Information Seeking":
                    logger.error(f"Fallback failed after switching to {fallback_category}")
                    return {"name": "Fallback failed", "text": fallback_category}, fallback_category  # Return both
                else:
                    logger.error(f"Fallback failed after switching to {fallback_category}")
                    return {"FunctionName": "Fallback failed", "Output": "Fallback failed"}, fallback_category  # Return both
        except Exception as e:
            if fallback_category == "Information Seeking":
                    logger.error(f"Fallback failed after switching to {fallback_category}")
                    return {"name": "Fallback failed", "text": f"{str(e)}"}, fallback_category  # Return both
            else:
                    logger.error(f"Fallback failed after switching to {fallback_category}")
                    return {"FunctionName": "Fallback failed", "Output": f"{str(e)}"}, fallback_category  # Return both
            
    async def execute_subquery(self, subquery, keywords, category, prefixes):
        """Executes the subquery based on its category (RAG or function calling)."""
        if category == 'Information Seeking':
            if prefixes:
            # Apply reranker based on confidence value generated by LLM
                vector_results = await self.rag.adv_query(query_text=subquery, keywords=keywords, top_k = 15, prefixes=prefixes)

                return vector_results
            else:
                return "No documents found"
        
        elif category == 'Function Calling':
            logger.info(f"Function is being called ...")
            if self.function_registry.values():
                logger.info(f"Function {self.function_registry.values()} is being called ...")
                return await self.function_caller.execute(subquery=subquery, tools=self.function_registry.values())
            else:
                return {"FunctionName": "No function available", "Output": "No tools registered."}
        else:
            raise ValueError("Invalid subquery category")
    
    async def _process_with_dependencies(self, initial_subquery, dependency_context, expected_format, dependency_usage):

        """
        Process subquery that has dependencies
        """
        reasoning = []
        messages = self.message_preparer.prepare_query_for_message(query = initial_subquery, system_prompt=f"{dependency_usage}. Provide answer in format: {expected_format}", history_messages=dependency_context)

        response = await self.small_llm.generate(
            messages=messages,
            max_new_tokens=512
        )

        logger.info(f"Reasoning result: {response}")

        reasoning.append({"name": "Reasoning result", "text": response})
        category = "Reasoning"
        return reasoning, category

    async def is_valid_result(self, result, subquery):
            """
            Uses the LLM to determine if the result is valid and complete for the given subquery.
            Handles different result types such as strings, lists, and dictionaries.
            """
            
            # Step 1: Check if the result is a string
            if isinstance(result, str):
                if not result or "error" in result.lower():  # Only apply lower() for strings
                    return False

            # Step 2: Check if the result is a dictionary
            elif isinstance(result, dict):
                # Check if any of the values in the dictionary contain "error", "No relevant documents found", or "no tool"
                if not result or any("error" in str(value).lower() for value in result.values()):
                    return False
                
                # Check specific "name" values
                if 'name' in result and result['name'] in ["No relevant documents found.", "no tool"]:
                    return False

            # Step 3: Check if the result is a list
            elif isinstance(result, list):
                if not result:
                    return False
                
                # Iterate through the list and check if any item contains "error" or specific "name" values
                for item in result:
                    if isinstance(item, dict) and 'name' in item:
                        if item['name'] in ["No relevant documents found.", "no tool"]:
                            return False
                    elif isinstance(item, str) and "error" in item.lower():
                        return False

            # Step 4: Handle unexpected result types
            else:
                if not result:
                    return False

            # If none of the above conditions triggered a False return, the result is considered valid
            return True 
    

