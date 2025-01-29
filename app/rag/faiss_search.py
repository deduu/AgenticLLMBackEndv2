# faiss_wrapper.py
import faiss
import numpy as np

class FAISS_search:
    def __init__(self, embedding_model):
        self.documents = []
        self.doc_ids = []
        self.embedding_model = embedding_model
        self.dimension = len(embedding_model.encode("embedding"))
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension))

    def add_document(self, doc_id, new_doc):
        self.documents.append(new_doc)
        self.doc_ids.append(doc_id)
        # Encode and add document with its index as ID
        embedding = self.embedding_model.encode([new_doc], convert_to_numpy=True).astype('float32')

        if embedding.size == 0:
            print("No documents to add to FAISS index.")
            return

        idx = len(self.documents) - 1
        id_array = np.array([idx]).astype('int64')
        self.index.add_with_ids(embedding, id_array)

    def remove_document(self, index):
        if 0 <= index < len(self.documents):
            del self.documents[index]
            del self.doc_ids[index]
            # Rebuild the index
            self.build_index()
        else:
            print(f"Index {index} is out of bounds.")

    def build_index(self):
        embeddings = self.embedding_model.encode(self.documents, convert_to_numpy=True).astype('float32')
        idx_array = np.arange(len(self.documents)).astype('int64')
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension))
        self.index.add_with_ids(embeddings, idx_array)

    def search(self, query, k):
        if self.index.ntotal == 0:
            # No documents in the index
            print("FAISS index is empty. No results can be returned.")
            return np.array([]), np.array([])  # Return empty arrays for distances and indices
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True).astype('float32')
        distances, indices = self.index.search(query_embedding, k)
        return distances[0], indices[0]
    
    def clear_documents(self) -> None:
        """
        Clears all documents from the FAISS index.
        """
        self.documents = []
        self.doc_ids = []
        # Reset the FAISS index
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension))
        print("FAISS documents cleared and index reset.")
    
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
