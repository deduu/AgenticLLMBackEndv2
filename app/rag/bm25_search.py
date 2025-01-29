# bm25_search.py
import asyncio
from rank_bm25 import BM25Okapi
import nltk
import string
from typing import List, Set, Optional
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer


def download_nltk_resources():
    """
    Downloads required NLTK resources synchronously.
    """
    resources = ['punkt', 'stopwords', 'wordnet', 'omw-1.4']
    for resource in resources:
        try:
            nltk.download(resource, quiet=True)
        except Exception as e:
            print(f"Error downloading {resource}: {str(e)}")

class BM25_search:
    # Class variable to track if resources have been downloaded
    nltk_resources_downloaded = False

    def __init__(self, remove_stopwords: bool = True, perform_lemmatization: bool = False):
        """
        Initializes the BM25search.

        Parameters:
        - remove_stopwords (bool): Whether to remove stopwords during preprocessing.
        - perform_lemmatization (bool): Whether to perform lemmatization on tokens.
        """
        # Ensure NLTK resources are downloaded only once
        if not BM25_search.nltk_resources_downloaded:
            download_nltk_resources()
            BM25_search.nltk_resources_downloaded = True  # Mark as downloaded

        self.documents: List[str] = []
        self.doc_ids: List[str] = []
        self.tokenized_docs: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.remove_stopwords = remove_stopwords
        self.perform_lemmatization = perform_lemmatization
        self.stop_words: Set[str] = set(stopwords.words('english')) if remove_stopwords else set()
        self.lemmatizer = WordNetLemmatizer() if perform_lemmatization else None

    def preprocess(self, text: str) -> List[str]:
        """
        Preprocesses the input text by lowercasing, removing punctuation,
        tokenizing, removing stopwords, and optionally lemmatizing.
        """
        text = text.lower().translate(str.maketrans('', '', string.punctuation))
        tokens = nltk.word_tokenize(text)
        if self.remove_stopwords:
            tokens = [token for token in tokens if token not in self.stop_words]
        if self.perform_lemmatization and self.lemmatizer:
            tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
        return tokens

    def add_document(self, doc_id: str, new_doc: str) -> None:
        """
        Adds a new document to the corpus and updates the BM25 index.
        """
        processed_tokens = self.preprocess(new_doc)
        
        self.documents.append(new_doc)
        self.doc_ids.append(doc_id)
        self.tokenized_docs.append(processed_tokens)
        # Ensure update_bm25 is awaited if required in async context
        self.update_bm25()
        print(f"Added document ID: {doc_id}")

    async def remove_document(self, index: int) -> None:
        """
        Removes a document from the corpus based on its index and updates the BM25 index.
        """
        if 0 <= index < len(self.documents):
            removed_doc_id = self.doc_ids[index]
            del self.documents[index]
            del self.doc_ids[index]
            del self.tokenized_docs[index]
            self.update_bm25()
            print(f"Removed document ID: {removed_doc_id}")
        else:
            print(f"Index {index} is out of bounds.")

    def update_bm25(self) -> None:
        """
        Updates the BM25 index based on the current tokenized documents.
        """
        if self.tokenized_docs:
            self.bm25 = BM25Okapi(self.tokenized_docs)
            print("BM25 index has been initialized.")
        else:
            print("No documents to initialize BM25.")


    def get_scores(self, query: str) -> List[float]:
        """
        Computes BM25 scores for all documents based on the given query.
        """
        processed_query = self.preprocess(query)
        print(f"Tokenized Query: {processed_query}")
        
        if self.bm25:
            return self.bm25.get_scores(processed_query)
        else:
            print("BM25 is not initialized.")
            return []

    def get_top_n_docs(self, query: str, n: int = 5) -> List[str]:
        """
        Returns the top N documents for a given query.
        """
        processed_query = self.preprocess(query)
        if self.bm25:
            return self.bm25.get_top_n(processed_query, self.documents, n)
        else:
            print("initialized.")
            return []
    
    def clear_documents(self) -> None:
        """
        Clears all documents from the BM25 index.
        """
        self.documents = []
        self.doc_ids = []
        self.tokenized_docs = []
        self.bm25 = None  # Reset BM25 index
        print("BM25 documents cleared and index reset.")
    
    def get_document(self, doc_id: str) -> str:
        """
        Retrieves a document by its document ID.
        
        Parameters:
        - doc_id (str): The ID of the document to retrieve.

        Returns:
        - str: The document text if found, otherwise an empty string.
        """
        try:
            index = self.doc_ids.index(doc_id)
            return self.documents[index]
        except ValueError:
            print(f"Document ID {doc_id} not found.")
            return ""


async def initialize_bm25_search(remove_stopwords: bool = True, perform_lemmatization: bool = False) -> BM25_search:
    """
    Initializes the BM25search with proper NLTK resource downloading.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, download_nltk_resources)
    return BM25_search(remove_stopwords, perform_lemmatization)


