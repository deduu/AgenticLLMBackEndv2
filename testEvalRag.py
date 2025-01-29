# test_rag_system.py
from tqdm.auto import tqdm
import asyncio
import logging
from typing import List, Optional, Any
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
# Adjust the Python path if necessary
import sys
import os
from pathlib import Path
import pprint
import json
import pandas as pd
import random
from IPython.display import display
from datasets import Dataset

# Ensure the 'app' directory is in the Python path
sys.path.append(str(Path(__file__).resolve().parent))

# Import necessary modules from your application
from app.rag.rag_pipeline import RAGSystem
from app.api.api_docs import load_file_function
from eval.load_file import proccess_file

from pprint import pprint
# Configure Pandas display options for readability
pd.set_option("display.max_colwidth", 500)  # Adjust column width
pd.set_option("display.max_columns", None)  # Show all columns
pd.set_option("display.width", 1000)  # Expand the display width

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Hugging Face inference client
repo_id = "mistralai/Mixtral-8x7B-Instruct-v0.1"
llm_client = InferenceClient(model=repo_id, timeout=120)

# LLM function
async def call_llm(inference_client: InferenceClient, prompt: str):
    response = inference_client.post(
        json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 1000},
            "task": "text-generation",
        },
    )
    return json.loads(response.decode())[0]["generated_text"]

# QA Generation Prompt
QA_generation_prompt = """
Your task is to write a factoid question and an answer given a context.
Your factoid question should be answerable with a specific, concise piece of factual information from the context.
Your factoid question should be formulated in the same style as questions users could ask in a search engine.
This means that your factoid question MUST NOT mention something like "according to the passage" or "context".

Provide your answer as follows:

Output:::
Factoid question: (your factoid question)
Answer: (your answer to the factoid question)

Now here is the context.

Context: {context}\n
Output:::
"""

QA_generation_prompt_ind = """
Tugas Anda adalah membuat pertanyaan faktual dan jawabannya berdasarkan sebuah konteks.
Pertanyaan faktual Anda harus dapat dijawab dengan informasi spesifik dan ringkas dari konteks yang diberikan.
Pertanyaan faktual harus dirumuskan dengan gaya yang sama seperti pertanyaan yang biasa diajukan di mesin pencari.
Ini berarti bahwa pertanyaan faktual Anda TIDAK BOLEH mengandung frasa seperti "berdasarkan teks" atau "berdasarkan konteks".

Berikan jawaban Anda dengan format berikut:

Output:::
Pertanyaan faktual: (pertanyaan faktual Anda)
Jawaban: (jawaban untuk pertanyaan faktual Anda)

Sekarang, berikut adalah konteksnya.

Konteks: {context}\n
Output:::
"""

question_groundedness_critique_prompt = """
You will be given a context and a question.
Your task is to provide a 'total rating' scoring how well one can answer the given question unambiguously with the given context.
Give your answer on a scale of 1 to 5, where 1 means that the question is not answerable at all given the context, and 5 means that the question is clearly and unambiguously answerable with the context.

Provide your answer as follows:

Answer:::
Evaluation: (your rationale for the rating, as a text)
Total rating: (your rating, as a number between 1 and 5)

You MUST provide values for 'Evaluation:' and 'Total rating:' in your answer.

Now here are the question and context.

Question: {question}\n
Context: {context}\n
Answer::: """

question_relevance_critique_prompt = """
You will be given a question.
Your task is to provide a 'total rating' representing how useful this question can be for Special Task Force for Upstream Oil and Gas Business Activities
Give your answer on a scale of 1 to 5, where 1 means that the question is not useful at all, and 5 means that the question is extremely useful.

Provide your answer as follows:

Answer:::
Evaluation: (your rationale for the rating, as a text)
Total rating: (your rating, as a number between 1 and 5)

You MUST provide values for 'Evaluation:' and 'Total rating:' in your answer.

Now here is the question.

Question: {question}\n
Answer::: """

question_standalone_critique_prompt = """
You will be given a question.
Your task is to provide a 'total rating' representing how context-independant this question is.
Give your answer on a scale of 1 to 5, where 1 means that the question depends on additional information to be understood, and 5 means that the question makes sense by itself.
For instance, if the question refers to a particular setting, like 'in the context' or 'in the document', the rating must be 1.
The questions can contain obscure technical nouns or acronyms like Gradio, Hub, Hugging Face or Space and still be a 5: it must simply be clear to an operator with access to documentation what the question is about.

For instance, "What is the name of the checkpoint from which the ViT model is imported?" should receive a 1, since there is an implicit mention of a context, thus the question is not independant from the context.

Provide your answer as follows:

Answer:::
Evaluation: (your rationale for the rating, as a text)
Total rating: (your rating, as a number between 1 and 5)

You MUST provide values for 'Evaluation:' and 'Total rating:' in your answer.

Now here is the question.

Question: {question}\n
Answer::: """

import re
import pandas as pd
import asyncio
from tqdm.auto import tqdm

async def generate_qa_pairs():
    """Generate QA pairs and evaluate them."""

    # Filepaths to process
    filepaths = [
        "./eval/datasets/md/Draft_POD.md",
        "./eval/datasets/md/ksmi.md",
    ]

    docs_processed = []
    for file_path in filepaths:
        docs = await proccess_file(file_path, chunk_size=2000, chunk_overlap=200)
        docs_processed.extend(docs)

    if not docs_processed:
        logger.warning("No documents were processed. Exiting...")
        return

    N_GENERATIONS = min(10, len(docs_processed))  
    logger.info(f"Generating {N_GENERATIONS} QA couples...")

    outputs = []
    for sampled_context in tqdm(random.sample(docs_processed, N_GENERATIONS)):
        output_QA_couple = await call_llm(llm_client, QA_generation_prompt_ind.format(context=sampled_context.page_content))

        try:
            if "Pertanyaan faktual:" not in output_QA_couple or "Jawaban:" not in output_QA_couple:
                raise ValueError("Invalid LLM output format")

            question = output_QA_couple.split("Pertanyaan faktual: ")[-1].split("Jawaban: ")[0].strip()
            answer = output_QA_couple.split("Jawaban: ")[-1].strip()

            if len(answer) > 500:
                logger.warning("Skipping entry due to answer length exceeding 500 characters.")
                continue

            outputs.append({
                "context": sampled_context.page_content,
                "question": question,
                "answer": answer,
                "source_doc": sampled_context.metadata["source"],
            })
        except Exception as e:
            logger.error(f"Skipping entry due to an error: {e}")
            continue

    if not outputs:
        logger.warning("No valid QA pairs generated. Exiting...")
        return

    df = pd.DataFrame(outputs)

    # Ensure "context" column exists
    if "context" in df.columns:
        df["context"] = df["context"].apply(lambda x: x[:500] + "..." if len(x) > 500 else x)
    else:
        logger.warning("Warning: 'context' column is missing in DataFrame.")
        logger.info(f"Available columns: {df.columns}")
        return

    print("\n--- Formatted Output ---\n")
    print(df.head(1).to_string(index=False))

    print("\n--- JSON-like Readable Output ---\n")
    pprint(outputs[:1])

    # --------------------------
    # CRITIQUE GENERATION
    # --------------------------
    print("\nGenerating critique for each QA couple...\n")

    async def evaluate_qa(output):
        """Run all three evaluations concurrently."""
        tasks = [
            call_llm(llm_client, question_groundedness_critique_prompt.format(context=output["context"], question=output["question"])),
            call_llm(llm_client, question_relevance_critique_prompt.format(question=output["question"])),
            call_llm(llm_client, question_standalone_critique_prompt.format(question=output["question"])),
        ]
        return await asyncio.gather(*tasks)

    for output in tqdm(outputs):
        try:
            groundedness_eval, relevance_eval, standalone_eval = await evaluate_qa(output)

            def extract_score_and_eval(evaluation_text):
                """Extracts 'Total rating' and 'Evaluation' from the model's response."""
                try:
                    score_match = re.search(r"Total rating:\s*(\d+)", evaluation_text)
                    eval_match = re.search(r"Evaluation:\s*(.+)", evaluation_text, re.DOTALL)
                    score = int(score_match.group(1)) if score_match else None
                    eval_text = eval_match.group(1).strip() if eval_match else None
                    return score, eval_text
                except Exception:
                    return None, None

            # Extract ratings
            groundedness_score, groundedness_eval_text = extract_score_and_eval(groundedness_eval)
            relevance_score, relevance_eval_text = extract_score_and_eval(relevance_eval)
            standalone_score, standalone_eval_text = extract_score_and_eval(standalone_eval)

            # Update output with critique scores
            output.update({
                "groundedness_score": groundedness_score,
                "groundedness_eval": groundedness_eval_text,
                "relevance_score": relevance_score,
                "relevance_eval": relevance_eval_text,
                "standalone_score": standalone_score,
                "standalone_eval": standalone_eval_text,
            })

        except Exception as e:
            logger.warning(f"Skipping critique evaluation due to error: {e}")
            continue

    # Create DataFrame
    generated_questions = pd.DataFrame.from_dict(outputs)

    # Display before filtering
    print("\nEvaluation dataset before filtering:\n")
    display(
        generated_questions[
            ["question", "answer", "groundedness_score", "relevance_score", "standalone_score"]
        ]
    )

    # Filter QA pairs with low scores
    generated_questions = generated_questions.loc[
        (generated_questions["groundedness_score"] >= 4)
        & (generated_questions["relevance_score"] >= 4)
        & (generated_questions["standalone_score"] >= 4)
    ]

    print("\n============================================")
    print("Final evaluation dataset:\n")
    display(
        generated_questions[
            ["question", "answer", "groundedness_score", "relevance_score", "standalone_score"]
        ]
    )


    eval_dataset = Dataset.from_pandas(generated_questions, split="train", preserve_index=False)

    print(f"eval_dataset: {eval_dataset}")

      

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
    query_text = "Apa pengertian Industri hulu migas"
    keywords = ["industri", "hulu", "migas  "]
    keywords = []
    top_k = 1

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

if __name__ == "__main__":
    # asyncio.run(test_load_file_with_markdown())
    asyncio.run(generate_qa_pairs())






