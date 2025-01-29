from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from urllib.parse import urlparse
import shutil
import os, logging, uuid

from app.crud.documents import process_uploaded_file
from app.utils.token_counter import TokenCounter
# ----------------------- Configuration ----------------------- #

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_url(path: str) -> bool:
    """
    Determines if the given path is a URL.

    Args:
        path (str): The path or URL to check.

    Returns:
        bool: True if it's a URL, False otherwise.
    """
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
    
file_load_router = APIRouter()

@file_load_router.post("/load_file/")
async def load_file(request: Request, folder: str = Form(...), file: UploadFile = File(...)):
    folder_path = os.path.join("user_data", folder)
    os.makedirs(folder_path, exist_ok=True)

    try:
        # Access `rag_system` from `app.state`
        # rag_system = request.app.state.rag_system
        # llm = request.app.state.llm_model

        agentic_system = request.app.state.agentic_system
    except AttributeError as e:
        raise HTTPException(status_code=500, detail="RAG system not initialized in app state")

    try:
        # Access the `id` from the form data
        form_data = await request.form()
        id = form_data.get("id")
        # Save the uploaded file to the specified folder
        file_path = os.path.join(folder_path, file.filename)
        logger.info(f"file path: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Load the file with RAG system processing
        documents = await process_uploaded_file(id = id, file_path=file_path, rag_system=agentic_system.rag, llm=agentic_system.small_llm)


             # Construct the pages data
        pages = [
            {
                "metadata": {"page": doc.metadata.get("page"), "source": doc.metadata.get("source")},

                "page_content": doc.page_content,
            }
            for doc in documents
        ]

        # Return the response with total_tokens, document_count, and pages
        total_tokens = agentic_system.rag.get_total_tokens()

        # print(f"Constructed pages: {pages}")
        return {
            "message": "File processed successfully",
            "total_tokens": total_tokens,
            "document_count": len(documents),
            "pages": pages,  # Include pages in the response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@file_load_router.post("/check_folder_name")
async def check_folder_name(folder: str = Form(...)):  # Use Form instead of Query
    folder_path = os.path.join("user_data", folder)
    logger.info(f"folder exists: {os.path.exists(folder_path)}")
    if os.path.exists(folder_path):
        return {"exists": True}
    return {"exists": False}

@file_load_router.delete("/delete_collection/")
async def delete_collection(request: Request, id: str = Query(...), folder: str = Query(...)):
    try:
        rag = request.app.state.rag_system  # Retrieve RAGSystem instance from app state
        folder_path = os.path.join("user_data", folder)

        # Log parameters (optional)
        print(f"Deleting collection: {folder}, ID prefix: {id}")

        # Step 1: Delete the folder if it exists
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            print(f"Folder '{folder}' deleted.")

        # Step 2: Identify and delete all document chunks in RAGSystem with the ID prefix
        matching_doc_ids = [doc_id for doc_id in rag.doc_ids if doc_id.startswith(f"{id}_")]
        
        if not matching_doc_ids:
            raise HTTPException(status_code=404, detail="No documents found with the specified collection ID prefix.")

        # Delete each matching document from RAGSystem
        for doc_id in matching_doc_ids:
            rag.delete_document(doc_id)

        return {
            "status": "success",
            "message": f"Collection '{folder}' with documents prefixed by '{id}' deleted successfully.",
        }

    except ValueError:
        raise HTTPException(status_code=404, detail="Collection ID not found.")
    except Exception as e:
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail="An error occurred while deleting the collection.")


async def load_file_function(filepaths: List[str],
    rag_system: Any):
  

    try:
        try:
            rag_system =  rag_system

        except AttributeError as e:
            raise HTTPException(status_code=500, detail="RAG system not initialized in app state")

        processed_files = []
        pages = []

        for path in filepaths:
            if is_url(path):
                pass
            else:
                logger.info(f"Processing local file: {path}")
                if os.path.exists(path):
                    try:
                        # Generate a unique UUID for the document
                        doc_id = str(uuid.uuid4())

                        # Process the local file
                        documents = await process_uploaded_file(id=doc_id, file_path=path, rag_system=rag_system)

                        # Append the document details to pages
                               # Construct the pages data
                        pages.extend([
                            {
                                "metadata": {"page": doc.metadata.get("page"), "source": doc.metadata.get("source")},

                                "page_content": doc.page_content,

                                
                            }
                            
                            for doc in documents
                        ])


                        logger.info(f"Successfully processed file: {path} with ID: {doc_id}")

                        # # Log the ID and a 100-character snippet of the document
                        # snippet = doc.page_content[:100].replace('\n', ' ').replace('\r', ' ')
                        # # Ensure 'doc_logger' is defined; if not, use 'logger' or define 'doc_logger'
                        # logger.info(f"ID: {doc_id}, Snippet: {snippet}")

                    except Exception as e:
                        logger.error(f"Error processing file {path}: {str(e)}")
                        processed_files.append({"path": path, "status": "error", "message": str(e)})
                else:
                    logger.error(f"File path does not exist: {path}")
                    processed_files.append({"path": path, "status": "not found"})
        
        # Get total tokens from RAG system
        total_tokens = rag_system.get_total_tokens() if hasattr(rag_system, "get_total_tokens") else 0
        
        return {
            "message": "File processing completed",
            "total_tokens": total_tokens,
            "document_count": len(filepaths),
            "pages": pages,
            "errors": processed_files,  # Include details about files that couldn't be processed
        }
    
    except Exception as e:
        logger.exception("Unexpected error during file processing")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")