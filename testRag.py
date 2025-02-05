# test_rag_system.py

import asyncio
import logging
from typing import List, Optional, Any
from sentence_transformers import SentenceTransformer

# Adjust the Python path if necessary
import sys
import os
from pathlib import Path
import pprint
import json

# Ensure the 'app' directory is in the Python path
sys.path.append(str(Path(__file__).resolve().parent))

# Import necessary modules from your application
from app.rag.rag_pipeline import RAGSystem
from app.api.api_docs import load_file_function


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

    
async def test_load_file_with_markdown():
    # Initialize the embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Replace with your model if different
    rag_system = RAGSystem(embedding_model)

    # Define the filepaths or URLs to load
    filepaths = [
        "./eval/datasets/md/Draft_POD.md",
        "./eval/datasets/md/ksmi.md",
        # Add more URLs or local file paths as needed
    ]

    # Load the files into the RAG system
    logger.info("Loading files into RAGSystem...")
    load_result = await load_file_function(filepaths=filepaths, rag_system=rag_system)
    logger.info(f"Load result:\n{json.dumps(load_result, indent=2, ensure_ascii=False)}")

    # Optionally, perform a sample query to verify
    query_text = "How does the classification of petroleum resources impact the approval and monitoring process of a POD?"
    keywords = ["classification", "petroleum", "approval", "monitoring", "POD"]
    keywords = []
    top_k = 10

    logger.info("Performing a sample query...")
    query_results = await rag_system.adv_query(query_text, keywords, top_k=top_k)

    logger.info(f"Query Results: {query_results}")

    # Print total tokens and context
    total_tokens = rag_system.get_total_tokens()
    context = rag_system.get_context()

    # print("\n=== RAG System Status ===")
    # print(f"Total Tokens Processed: {total_tokens}")
    # print(f"Context:\n{context}")

    # Optionally, save the state
    # rag_system.save_state("test_rag_system")  # Uncomment to save state

    # Optionally, load the state
    # rag_system.load_state("test_rag_system")  # Uncomment to load state

    # LLM implementation
    from app.models.parallel_model_pool import ParallelModelPool
    from app.config_loader import load_model_configs
    config_path = "./config.yaml"
    small_model_configs =  load_model_configs(config_path, "small")
    small_model_pool = ParallelModelPool(model_configs=small_model_configs, num_instances=1)

    rag_prompt = """
    ### Context (Retrieved Documents):
    {context}

    ### User Question:
    {question}

    ### Instructions:
    1. **Identify Relevant Information:** Extract key facts and details from the retrieved context that are directly related to the user's question.
    2. **Reasoning & Inference:** If the answer is explicitly stated, provide it concisely. If implicit, use logical reasoning to infer a response.
    3. **Uncertainty Handling:** If the information is insufficient or ambiguous, state: "Based on the available data, I cannot provide a definitive answer."
    4. **Structured Output:** Provide the answer in a clear, well-structured format.
    """
    async def call_llm(llm: Any, prompt: str) -> str:
        """Concrete implementation of the call_llm function."""
        if hasattr(llm, "generate"):
            response = await llm.generate(messages=[{"role": "user", "content": prompt}], max_new_tokens=5000)
            return response

        else:
            raise TypeError(f"Unsupported LLM type: {type(llm)}")
    
    
    
    response = await call_llm(llm=small_model_pool, prompt=rag_prompt.format(context=query_results, question=query_text))

    print(f"LLM Response: {response}")

if __name__ == "__main__":
    asyncio.run(test_load_file_with_markdown())






