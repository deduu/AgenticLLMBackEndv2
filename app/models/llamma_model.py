# app/models/llamma_model.py
from app.models.base_model import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from typing import List, Dict, Any, Optional
import torch
import logging
import threading
import time as time_module
import json
import gc
import asyncio
from fastapi import HTTPException

from app.handlers.context_handler import ContextPreparer

logger = logging.getLogger(__name__)

class llammaModel(BaseModel):
    """
    Implementation for llamma Instruct model.
    """
    
    def __init__(self, model_path: str, device: str, dtype=torch.float16, system_prompt:str=None, quantization: Optional[str] = None):
        super().__init__(model_path, device, system_prompt=system_prompt, dtype=dtype, quantization=quantization)   

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = self.load_model()
    def load_model(self):
        # Check quantization type and load the model accordingly
        if self.quantization == "4bit":
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.dtype == "float16" else torch.float32,
                device_map="auto",
                load_in_4bit=True
            )
        elif self.quantization == "8bit":
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.dtype == "float16" else torch.float32,
                device_map="auto",
                load_in_8bit=True
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if self.dtype == "float16" else torch.float32,
                device_map="auto"
            )
        logger.info(f"Loaded {self.model_path} model on {self.device}")
        return model
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, 
            torch_dtype=dtype
        ).to(device)
        logger.info(f"Loaded {model_path} model on {device}")
    
    async def generate_function_call(self, messages: List[Dict[str, str]], tools: List[Any]) -> str:
        # Implement llamma-specific function call generation
        # This could involve specific preprocessing or postprocessing
        inputs = self.tokenizer.apply_chat_template(
            messages,
            tools=tools,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        output = self.model.generate(
            **inputs,
            max_new_tokens=128
        )
        response = self.tokenizer.decode(output[0][len(inputs["input_ids"][0]):])
        logger.info(f"llamma generated function call: {response}")
        return response
    
    async def generate_text_stream(
        self, 
        query: str,  
        context: None,
        history_messages: Optional[List[Dict]] = None, 
        max_new_tokens: int = 1024, 
        temperature: float = 0.7, 
        top_p: float = 0.9):

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
                {"role": "system", "content": self.system_prompt},
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
            inputs = {k: v.to(self.device) for k, v in input_ids.items()}
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
                target=self.model.generate, 
                kwargs=generation_kwargs
            )
            generation_thread.start()
            logger.debug(f"Started generation thread on {self.device}")

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
        
    
    async def generate_text(self, messages: List[Dict[str, str]], max_new_tokens: int) -> str:
       
        input_ids = self.tokenizer.apply_chat_template(messages,add_generation_prompt=True, return_dict=True, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in input_ids.items()}
        try:
            with torch.no_grad():
                output = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    top_k=50,
                    top_p=0.95,
                    # eos_token_id=self.tokenizer.eos_token_id,
                    # pad_token_id=self.tokenizer.eos_token_id
                )
            generated_response = self.tokenizer.decode(output[0][len(inputs["input_ids"][0]):]).strip().replace('<|eot_id|>', '')
       
            logger.info(f"llamma generated text: {generated_response}")
            return generated_response
        finally:
            del input_ids
            del inputs  
            gc.collect()
            torch.cuda.empty_cache()
    
