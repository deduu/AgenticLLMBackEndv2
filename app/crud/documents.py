# app/crud.py
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, CSVLoader, UnstructuredExcelLoader, UnstructuredMarkdownLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import os
import logging
import pprint

from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_pdf_with_langchain(file_path):
    """
    Loads and extracts text from a PDF file using LangChain's PyPDFLoader.

    Parameters:
        file_path (str): Path to the PDF file.

    Returns:
        List[Document]: A list of LangChain Document objects with metadata.
    """

    loader = PyPDFLoader(file_path, extract_images=True)
   
    documents = loader.load()

    return documents  # Returns a list of Document objects

async def load_file_with_langchain(file_path: str):
    """
    Loads and extracts text from a PDF or DOCX file using LangChain's appropriate loader.

    Parameters:
        file_path (str): Path to the file (PDF or DOCX).

    Returns:
        List[Document]: A list of LangChain Document objects with metadata.
    """
    # Determine the file extension
    _, file_extension = os.path.splitext(file_path)
    
    # Choose the loader based on file extension
    if file_extension.lower() == '.pdf':
        loader = PyPDFLoader(file_path)
    elif file_extension.lower() == '.docx':
        loader = Docx2txtLoader(file_path)
    elif file_extension.lower() == '.csv':
        loader = CSVLoader(file_path)
    elif file_extension.lower() == '.xlsx':
        loader = UnstructuredExcelLoader(file_path)
    elif file_extension.lower() == '.md':
        loader = UnstructuredMarkdownLoader(file_path)
    else:
        raise ValueError("Unsupported file format. Please provide a PDF or DOCX file.")
    
    # Load the documents
    documents = loader.load()

    return documents

async def split_documents(documents, chunk_size=10000, chunk_overlap=1000):
    """
    Splits documents into smaller chunks with overlap.

    Parameters:
        documents (List[Document]): List of LangChain Document objects.
        chunk_size (int): The maximum size of each chunk.
        chunk_overlap (int): The number of characters to overlap between chunks.

    Returns:
        List[Document]: List of chunked Document objects.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    split_docs = text_splitter.split_documents(documents)
    return split_docs

async def process_uploaded_file(
    id, file_path,
    rag_system=None, 
    chunk_size=5000, 
    chunk_overlap=500, 
    load_only=False, 
    llm=None
):
    """
    Loads, splits, and optionally adds a document to a RAG system.

    Parameters:
        file_path (str): Path to the document file (PDF or DOCX).
        rag_system (RAGSystem, optional): An instance of RAGSystem to add documents to. Default is None.
        chunk_size (int, optional): Size of each chunk in characters. Default is 10000.
        chunk_overlap (int, optional): Number of overlapping characters between chunks. Default is 1000.
        load_only (bool, optional): If True, only load and split the document without adding it to RAG. Default is False.

    Returns:
        List[Document]: List of split document chunks.
    """
    print(f"file path {file_path}")
    # Determine the file extension
    file_name, file_extension = os.path.splitext(file_path)
    try:
        # Load the document using LangChain
        documents = await load_file_with_langchain(file_path)
        logger.info(f"Loaded document: {file_path}")

         # Concatenate all pages to get the full document text for context generation
        # whole_document_content = "\n".join([doc.page_content for doc in documents])

    except Exception as e:
        logger.error(f"Failed to load document {file_path}: {e}")
        raise RuntimeError(f"Error loading document: {file_path}") from e

    try:
        # Split the loaded document into chunks
        split_docs = await split_documents(documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        # logger.info(f"Split_docs:\n{pprint.pformat(split_docs)}")
        logger.info(f"Document split into {len(split_docs)} chunks with chunk_size={chunk_size} and chunk_overlap={chunk_overlap}")

    except Exception as e:
        logger.error(f"Failed to split document {file_path}: {e}")
        raise RuntimeError(f"Error splitting document: {file_path}") from e

    # # Generate context for each chunk if llm is provided
    # if llm:
    #     for doc in split_docs:
    #         try:
    #             context = await llm.generate_context(doc, whole_document_content=whole_document_content)
    #             # Add context to the beginning of the page content
    #             doc.page_content = f"{context.replace('<|eot_id|>', '')}\n\n{doc.page_content}"
    #             logger.info(f"Context generated and added for chunk {split_docs.index(doc)}")
    #         except Exception as e:
    #             logger.error(f"Failed to generate context for chunk {split_docs.index(doc)}: {e}")
    #             raise RuntimeError(f"Error generating context for chunk {split_docs.index(doc)}") from e
            
    # Add to RAG system if rag_system is provided and load_only is False
    if rag_system and not load_only:
        try:
            for idx, doc in enumerate(split_docs):
                        doc_id = f"{id}_{file_name}_page{doc.metadata.get('page', 'unknown')}_chunk{idx}" # Create a unique ID per document chunk
                        rag_system.add_document(
                            doc_id=doc_id,
                            text=doc.page_content,
                            meta_data=doc.metadata,
                        )
                        print(f"doc_id: {doc_id}")
                        print(f"meta_data: {doc.metadata}")

                        # print(f"New Page Content: {doc.page_content}")
            logger.info(f"Document chunks successfully added to RAG system for file {file_path}")

        except Exception as e:
            logger.error(f"Failed to add document chunks to RAG system for {file_path}: {e}")
            raise RuntimeError(f"Error adding document to RAG system: {file_path}") from e
    else:
        logger.info(f"Loaded and split document {file_path}, but not added to RAG system (load_only={load_only})")

    return split_docs




