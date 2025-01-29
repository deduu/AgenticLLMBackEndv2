# rag_pipeline.py

import numpy as np

import pickle
import os
import logging
import asyncio

from app.rag.bm25_search import BM25_search
from app.rag.faiss_search import FAISS_search
from app.rag.hybrid_search import Hybrid_search
from app.utils.token_counter import TokenCounter


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from keybert import KeyBERT
import asyncio

def extract_keywords_async(doc, threshold=0.4, top_n = 5):
    kw_model = KeyBERT()
    keywords = kw_model.extract_keywords(doc, threshold=threshold, top_n=top_n)
    keywords = [key for key, _ in keywords]
    return keywords

# rag.py
class RAGSystem:
    def __init__(self, embedding_model):
        self.token_counter = TokenCounter()
        self.documents = []
        self.doc_ids = []
        self.results = []
        self.meta_data = []
        self.embedding_model = embedding_model
        self.bm25_wrapper = BM25_search()
        self.faiss_wrapper = FAISS_search(embedding_model)
        self.hybrid_search = Hybrid_search(self.bm25_wrapper, self.faiss_wrapper)

    def add_document(self, doc_id, text, meta_data=None):
        self.token_counter.add_document(doc_id, text)
        self.doc_ids.append(doc_id)
        self.documents.append(text)
        self.meta_data.append(meta_data)
        self.bm25_wrapper.add_document(doc_id, text)
        self.faiss_wrapper.add_document(doc_id, text)

    def delete_document(self, doc_id):
        try:
            index = self.doc_ids.index(doc_id)
            del self.doc_ids[index]
            del self.documents[index]
            self.bm25_wrapper.remove_document(index)
            self.faiss_wrapper.remove_document(index)
            self.token_counter.remove_document(doc_id)
        except ValueError:
            logging.warning(f"Document ID {doc_id} not found.")

    async def adv_query(self, query_text, keywords, top_k=5, prefixes=None):
        results = await self.hybrid_search.advanced_search(
            query_text,
            keywords=keywords,
            top_n=top_k,
            threshold=0.43,
            prefixes=prefixes
        )
        retrieved_docs = []
        if results:
            seen_docs = set()
            for doc_id, score in results:
                if doc_id not in seen_docs:
                     # Check if the doc_id exists in self.doc_ids
                    if doc_id not in self.doc_ids:
                        logger.error(f"doc_id {doc_id} not found in self.doc_ids")
                    seen_docs.add(doc_id)
                  
                    # Fetch the index of the document
                    try:
                        index = self.doc_ids.index(doc_id)
                    except ValueError as e:
                        logger.error(f"Error finding index for doc_id {doc_id}: {e}")
                        continue

                     # Validate index range
                    if index >= len(self.documents) or index >= len(self.meta_data):
                        logger.error(f"Index {index} out of range for documents or metadata")
                        continue

                    doc = self.documents[index]
                    
                    meta_data = self.meta_data[index]
                    # Extract the file name and page number
                    # file_name = meta_data['source'].split('/')[-1]  # Extracts 'POJK 31 - 2018.pdf'
                    # page_number = meta_data.get('page', 'unknown')
                    # url = meta_data['source']
                    # file_name = meta_data.get('source', 'unknown_source').split('/')[-1]  # Safe extraction
                    # page_number = meta_data.get('page', 'unknown')  # Default to 'unknown' if 'page' is missing
                    url = meta_data.get('source', 'unknown_url')  # Default URL fallback

                    # logger.info(f"file_name: {file_name}, page_number: {page_number}, url: {url}")

                    # Format as a single string
                    # content_string = f"'{file_name}', 'page': {page_number}"
                    # doc_name = f"{file_name}"
                  
                    self.results.append(doc)
                    retrieved_docs.append({"url":url, "text": doc})
            return retrieved_docs
        else:
            return [{"url": "None.", "text": None}]

    def get_total_tokens(self):
        return self.token_counter.get_total_tokens()
    def get_context(self):
        context = "\n".join(self.results)
        return context

    def save_state(self, path):
    # Save doc_ids, documents, and token counter state
        with open(f"{path}_state.pkl", 'wb') as f:
            pickle.dump({
                "doc_ids": self.doc_ids,
                "documents": self.documents,
                "meta_data": self.meta_data,
                "token_counts": self.token_counter.doc_tokens
            }, f)

    def load_state(self, path):
        if os.path.exists(f"{path}_state.pkl"):
            with open(f"{path}_state.pkl", 'rb') as f:
                state_data = pickle.load(f)
                self.doc_ids = state_data["doc_ids"]
                self.documents = state_data["documents"]
                self.meta_data = state_data["meta_data"]
                self.token_counter.doc_tokens = state_data["token_counts"]

            # Clear and rebuild BM25 and FAISS
            self.bm25_wrapper.clear_documents()
            self.faiss_wrapper.clear_documents()
            for doc_id, document in zip(self.doc_ids, self.documents):
                self.bm25_wrapper.add_document(doc_id, document)
                self.faiss_wrapper.add_document(doc_id, document)

            self.token_counter.total_tokens = sum(self.token_counter.doc_tokens.values())
            logging.info("System state loaded successfully with documents and indices rebuilt.")
        else:
            logging.info("No previous state found, initializing fresh state.")
            self.doc_ids = []
            self.documents = []
            self.meta_data = []  # Reset meta_data
            self.token_counter = TokenCounter()
            self.bm25_wrapper = BM25_search()
            self.faiss_wrapper = FAISS_search(self.embedding_model)
            self.hybrid_search = Hybrid_search(self.bm25_wrapper, self.faiss_wrapper)