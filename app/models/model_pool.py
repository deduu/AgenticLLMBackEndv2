# app/models/model_pool.py
import asyncio
import torch
import logging
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
import threading
import time as time_module
import json
import gc
from app.utils.message_utils import extract_tool_calls, call_function, function_registry
from app.handlers.context_handler import ContextPreparer
from app.services.message_preparer import MessagePreparer
from app.handlers.response_handler import ResponseHandler
from app.utils.system_prompt import *
from app.utils.exceptions import ToolExecutionError

from .llm_interface import LLMInterface

logger = logging.getLogger(__name__)

class ParallelModelPool(LLMInterface):
    """
    Manages a pool of model instances for parallel inference across multiple CUDA devices.
    Utilizes an asyncio.Queue to handle request queuing when all models are busy.
    """
    def __init__(
        self, 
        model_path: str, 
        num_instances: int = 4, 
        dtype=torch.float16, 
        devices: Optional[List[str]] = None
    ):
        """
        Initializes the model pool.

        Args:
            model_path (str): Path or name of the pretrained model.
            num_instances (int): Number of model instances to load.
            dtype: Data type for the model parameters.
            devices (Optional[List[str]]): Specific devices to load models onto. 
                                           If None, all available CUDA devices are used.
        """
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.queue = asyncio.Queue(maxsize=num_instances)
        self.model_instances = []
        self.message_preparer = MessagePreparer()
        # self.tool_executor =  ToolCallExtractor(tools=tools)
        self.response_handler = ResponseHandler()

        # Detect available CUDA devices if not specified
        if devices is None:
            available_cuda = torch.cuda.device_count()
            devices = [f"cuda:{i}" for i in range(available_cuda)] if available_cuda > 0 else ["cpu"]
            if not devices:
                devices = ["cpu"]

        logger.info(f"Using devices: {devices}")

        for i in range(num_instances):
            try:
                # Assign devices in a round-robin fashion if instances exceed devices
                device = devices[i % len(devices)]
                
                logger.debug(f"Loading model instance {i} on {device}")

                model = AutoModelForCausalLM.from_pretrained(
                    model_path, 
                    torch_dtype=dtype
                ).to(device)
                
                model_instance = {
                    'model': model, 
                    'device': device
                }
                self.model_instances.append(model_instance)
                
                # Enqueue the model instance as available
                self.queue.put_nowait(model_instance)
                
                logger.info(f"Loaded and enqueued model instance {i} on {device}")
            except Exception as e:
                logger.error(f"Failed to load model instance {i} on {device}: {e}")

    @property
    def tokenizer(self):
        """
        Returns the tokenizer instance.
        """
        return self._tokenizer

    @property
    def device(self):
        """
        Since ParallelModelPool manages multiple devices, 
        you can return a representative string or handle it differently.
        """
        return "pool"  # Indicates that multiple devices are managed
    
    async def get_free_model(self, timeout: Optional[float] = None):
        """
        Retrieves a free model instance from the queue.
        Waits until a model becomes available or until timeout.

        Args:
            timeout (Optional[float]): Maximum time to wait for a model.

        Returns:
            dict: A dictionary containing the model and its device.

        Raises:
            HTTPException: If no model becomes available within the timeout.
        """
        try:
            model_instance = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            logger.debug(f"Acquired model on {model_instance['device']}")
            return model_instance
        except asyncio.TimeoutError:
            logger.warning("No model instances available and timeout reached.")
            raise HTTPException(503, "No model instances available. Please try again later.")

    async def release_model(self, model_instance):
        """
        Releases a model instance back to the queue.

        Args:
            model_instance (dict): The model instance to release.
        """
        await self.queue.put(model_instance)
        logger.debug(f"Released model on {model_instance['device']} back to the queue")

    async def generate_function_call(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Any]
    ) -> str:
        """
        Generate a response using the model pool.
        
        :param messages: The messages to send to the LLM.
        :param max_new_tokens: The maximum number of tokens to generate.
        :return: The generated response as a string.
        """
        
        # Acquire a free model
        model_instance = await self.get_free_model(timeout=30)
        tool_response = []
        chart_data = []
          # Adjust timeout as needed
        try:
            model = model_instance['model']
            device = model_instance['device']
            logger.info(f"tools: {tools}")
            inputs = self._tokenizer.apply_chat_template(
                messages,
                tools=tools,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt"
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            out = model.generate(
                **inputs,
                max_new_tokens=128
                # eos_token_id=self.tokenizer.eos_token_id,
                # pad_token_id=self.tokenizer.eos_token_id
            )
            input_string = self.tokenizer.decode(out[0][len(inputs["input_ids"][0]):])
            # Extract only the newly generated part
            logger.info(f"Generated input_string: {input_string}")
            return input_string
        
        except Exception as e:
            logger.error(f"Error during generation: {e}")
            raise
        finally:
            await self.release_model(model_instance)


    async def generate_text_stream(
        self, 
        query: str, 
        context: None,
        history_messages: Optional[List[Dict]] = None, 
        max_new_tokens: int = 1024, 
        temperature: float = 0.7, 
        top_p: float = 0.9,
        timeout: Optional[float] = None  # Optional timeout for acquiring a model
    ):
        """
        Generates text in a streaming fashion using an available model instance.
        Requests are queued if all model instances are busy.

        Args:
            query (str): The input prompt for text generation.
            history_messages (Optional[List[Dict]]): Previous messages in the conversation.
            max_new_tokens (int): Maximum number of tokens to generate.
            temperature (float): Sampling temperature.
            top_p (float): Top-p sampling threshold.
            timeout (Optional[float]): Maximum time to wait for a model instance.

        Yields:
            str: Generated text chunks and metrics as Server-Sent Events (SSE).
        """
        model_instance = await self.get_free_model(timeout=timeout)
        try:
           
            history_messages = history_messages if history_messages else ""
   

            # Prepare context string using ContextPreparer
            context_preparer = ContextPreparer()
            context_str = context_preparer.prepare_context(context)

            logger.info(f"context_Str: {context_str}")

            # Prepare the user message with constraints and instructions
            user_message = f"""
            Please answer the following question using **only** the provided context and function call responses. **Do not use any external information or your own knowledge.**

            When you reference information from the context or function call responses, you **must** cite the source from the provided metadata by including an inline citation in the format `[Document Name](URL)(Page X)` for documents, or `[Function Name](Reference)` for function calls.

            ### Example of metadata in the retrieved documents:

            {{"Subquery-1": {{"Source": [{{"name": "Resume.pdf", "page":1, "url": "user_data/Candidate/Resume.pdf", "text": "Document Content"}}], "Type": "RAG"}}}}

            The format of the citation becomes `[Resume.pdf](user_data/Candidate/Resume.pdf)(page 1)`

            ### Example of metadata in the function call responses:

            {{'Subquery-1': {{'Source': [{{'FunctionName': [{{'name': 'google_search', 'arguments': {{'query': '2024 US election', 'num_results': '10'}}}}], 'Output': 'output of the function call'}}], 'Type': 'Action'}}}}

            The format of the citation becomes `[google_search](query: '2024 US election', num_results: '10')`

            Ensure that the citations are properly formatted as clickable links in Markdown.

            If the context and function call responses do not contain enough information to answer the question, politely inform the user of this limitation.

            ---

            **Question:**

            {query}

            ---

            **Context:**

            {context_str}

            ---

            **Instructions:**

            - Provide a clear and concise answer to the question.
            - Do not include any information that is not in the provided context or function call responses.
            - If the answer cannot be found in the context or function call responses, state that the information is not available.
            - **Every time** you use information from the context or function call responses, include an inline citation immediately after the information.
            - Always prioritize the most recent information if there are conflicting information from the context or function call responses.

            **Example:**

            "According to [Resume.pdf](user_data/Candidate/Resume.pdf)(page 1), ..."

            "As provided by [Function Name], ..."

            **Citation Format requirement:**
            - Citation Format: `[Document Name](URL)(page X)`
            - Place citation IMMEDIATELY after used information
            - Use metadata from the context to get the right page number
                
            **Validation:**
            - Don't cite Document Name that does not have a page number.
            - Double check if you have cited the correct document.

            ---

            **Answer:**
            """


            user_message = user_message if context else query
            messages = [
                {"role": "system", "content": agentic_prompt},
                {"role": "system", "content": f"Message history: {history_messages}"},
                # {"role": "system", "content": f"Context Information: {context}"},
                {"role": "user", "content": user_message}
            ]
            logger.info(f"Generating text for messages: {messages}")

            # Prepare inputs using tokenizer
            input_ids = self.tokenizer.apply_chat_template(
                messages, 
                add_generation_prompt=True, 
                return_tensors="pt", 
                return_dict=True
            )
            inputs = {k: v.to(model_instance['model'].device) for k, v in input_ids.items()}
            streamer = TextIteratorStreamer(
                self.tokenizer, 
                skip_prompt=True, 
                skip_special_tokens=True
            )

            # Define generation parameters
            generation_kwargs = {
                **inputs,
                'streamer': streamer,
                'max_new_tokens': max_new_tokens,
                'temperature': temperature,
                'top_p': top_p,
                'do_sample': True,
                'pad_token_id': self.tokenizer.eos_token_id,
            }

            # Start model generation in a separate thread
            generation_thread = threading.Thread(
                target=model_instance['model'].generate, 
                kwargs=generation_kwargs
            )
            generation_thread.start()
            logger.debug(f"Started generation thread on {model_instance['device']}")

            loop = asyncio.get_event_loop()

            # Define a synchronous function to get the next chunk
            def get_next_chunk():
                try:
                    return next(streamer)
                except StopIteration:
                    return None  # Indicate the end of the stream

            token_count = 0
            start_time = time_module.perf_counter()

            # Stream response using an asynchronous generator
            while True:
                next_text = await loop.run_in_executor(None, get_next_chunk)
                if next_text is None:
                    break
                yield next_text # SSE format
                token_count += 1

            # Ensure the generation thread has finished
            generation_thread.join()

            # Cleanup
            del input_ids
            del inputs
            del streamer
            del generation_thread

            # Force garbage collection
            gc.collect()
            torch.cuda.empty_cache()

            # Compute metrics
            end_time = time_module.perf_counter()
            latency = end_time - start_time
            tokens_per_second = token_count / latency if latency > 0 else 0

            # Create metrics dict
            metrics = {
                
                    "latency": latency,
                    "tokens": token_count,
                    "tps": tokens_per_second
                
            }

            # Send metrics as a JSON string
            yield json.dumps({"metrics": metrics})

        except asyncio.CancelledError:
            logger.info("Client disconnected. Releasing model instance.")
            raise  # Ensures the finally block executes
        except HTTPException as he:
            # Re-raise HTTP exceptions to be handled by FastAPI
            raise he
        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise HTTPException(500, f"Generation error: {e}")
        finally:
            # Release the model instance back to the queue regardless of success or failure
            await self.release_model(model_instance)

    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        max_new_tokens: int = 128
    ) -> str:
        """
        Generate a response using the model pool.
        
        :param messages: The messages to send to the LLM.
        :param max_new_tokens: The maximum number of tokens to generate.
        :return: The generated response as a string.
        """
        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)
        
        # Acquire a free model
        model_instance = await self.get_free_model(timeout=30)  # Adjust timeout as needed
        try:
            model = model_instance['model']
            device = model_instance['device']
            
            inputs = self._tokenizer(prompt, return_tensors="pt").to(device)
            output = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                eos_token_id=self._tokenizer.eos_token_id,
                pad_token_id=self._tokenizer.eos_token_id
            )
            response = self._tokenizer.decode(output[0], skip_special_tokens=True)
            # Extract only the newly generated part
            generated_response = response[len(prompt):].strip()
            return generated_response
        except Exception as e:
            logger.error(f"Error during generation: {e}")
            raise
        finally:
            await self.release_model(model_instance)
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert messages to a single prompt string.
        
        :param messages: List of messages with roles and content.
        :return: A concatenated prompt string.
        """
        prompt = ""
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            prompt += f"{role}: {content}\n"
        prompt += "assistant:"
        return prompt
    
    async def process_user_query(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Any]
    ) -> str:
        """
        Process the user query by interacting with the LLM and executing tool calls.

        :param messages: The prepared messages to send to the LLM.
        :param tools: The list of tools available for execution.
        :return: The final response from the LLM.
        """
        
        tool_response = []
        chart_data = []

        # logger.info(f"Message input to LLM: {messages}")
        
        # Generate initial response from LLM
        try:
            initial_response = await self.generate_function_call(messages = messages, tools = function_registry.values())
        except Exception as e:
            logger.error(f"Error generating initial response: {e}")
            raise

        logger.info(f"Initial LLM response: {initial_response}")

        tool_calls = extract_tool_calls(initial_response)

        logger.info(f"Extracted tool calls: {tool_calls}")

        for idx, tool_call in enumerate(tool_calls):
            try:
                function_name, result = await call_function(tool_call)
            

                messages.append({
                    "role": "assistant", 
                    "content": "", 
                    "tool_calls": [{"type": "function", "function": tool_call}]
                })

                if not result:
                    error_message = f"Empty result from {function_name}"
                    messages.append({"role": "assistant", "content": error_message})
                    logger.warning(f"Tool Call {idx} Error: {error_message}")
                    continue

                data = {
                    "chartType": result.get("chartType", ""),
                    "data": result.get("data", []),
                    "config": result.get("config", {}),
                    "chartTitle": result.get("chartTitle", "")
                }
                logger.info(f"Tool result: {result}")

                chart_data.append(data)

                has_chart = "config" in result

                if not has_chart:
                    messages.append({"role": "ipython", "name": function_name, "content": result})
                else:
                    messages.append({"role": "ipython", "name": function_name, "content": result.get("rawData", {})})

            except ToolExecutionError as te:
                messages.append({"role": "assistant", "content": str(te)})
                logger.error(f"Tool Call {idx} Error: {str(te)}")
            except Exception as e:
                error_message = f"Unexpected error: {str(e)}"
                messages.append({"role": "assistant", "content": error_message})
                logger.error(f"Tool Call {idx} Unexpected Error: {error_message}")

        logger.info(f": {messages}")

        # Handle message transformations
        messages = self.response_handler.handle_messages(messages)

        # Generate final response from LLM
        try:
            final_response = await self.generate(messages, max_new_tokens=512)
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            raise

        tool_response.append({
            "FunctionName": tool_calls,
            "chartData": chart_data,
            "Output": final_response.strip().replace('<|eot_id|>', '')
        })
        logger.info(f"Final tool_response: {tool_response}")

        return tool_response
 
