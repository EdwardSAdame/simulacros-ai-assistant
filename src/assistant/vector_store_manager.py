# src/assistant/vector_store_manager.py
import logging
import requests
from io import BytesIO
from typing import List, Optional, Tuple
from src.config.settings import get_openai_client

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    Handles interactions with OpenAI's File Search (Vector Store) API.
    Responsible for creating stores, uploading files, and managing the lifecycle.
    """

    def __init__(self):
        self.client = get_openai_client()

    def _download_file_content(self, url: str) -> Optional[Tuple[str, BytesIO]]:
        """Downloads a file from a URL into a memory buffer for OpenAI upload."""
        try:
            # Added timeout to prevent hanging forever
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Extract filename from URL or default to generic
            filename = url.split("/")[-1].split("?")[0]
            if not filename:
                filename = "document.pdf"
                
            return (filename, BytesIO(response.content))
        except Exception as e:
            logger.error(f"Failed to download file from {url}: {e}")
            return None

    def create_arena_knowledge_base(self, arena_name: str, file_urls: List[str]) -> Optional[str]:
        """
        Creates a Vector Store for an Arena and processes the initial files.
        Returns the vector_store_id.
        """
        if not file_urls:
            return None

        try:
            logger.info(f"Creating Vector Store for Arena: {arena_name}")
            
            # 1. Create the Vector Store Container
            vector_store = self.client.vector_stores.create(
                name=f"Arena: {arena_name}"
            )
            
            # 2. Upload and Attach Files
            valid_streams = []
            
            # Download all files first
            for url in file_urls:
                file_data = self._download_file_content(url)
                if file_data:
                    # OpenAI expects a tuple (filename, file_obj)
                    valid_streams.append(file_data)

            if not valid_streams:
                logger.warning("No valid files could be downloaded for Arena creation.")
                # We return the ID anyway so the Arena can be updated later
                return vector_store.id 

            # 3. Batch Upload to Vector Store
            file_batch = self.client.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id,
                files=valid_streams
            )
            
            logger.info(f"Vector Store Created: {vector_store.id} | Status: {file_batch.status}")
            logger.info(f"File Counts: {file_batch.file_counts}")
            
            return vector_store.id

        except Exception as e:
            logger.error(f"Error creating Arena Knowledge Base: {e}")
            return None

    def add_files_to_arena(self, vector_store_id: str, file_urls: List[str]):
        """
        Adds new files to an existing Vector Store.
        """
        if not vector_store_id or not file_urls:
            return

        try:
            valid_streams = []
            for url in file_urls:
                file_data = self._download_file_content(url)
                if file_data:
                    valid_streams.append(file_data)
            
            if valid_streams:
                logger.info(f"Uploading {len(valid_streams)} files to existing store: {vector_store_id}")
                self.client.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vector_store_id,
                    files=valid_streams
                )
                logger.info(f"Successfully added files to store {vector_store_id}")

        except Exception as e:
            logger.error(f"Failed to add files to store {vector_store_id}: {e}")

    def delete_vector_store(self, vector_store_id: str) -> bool:
        """
        Permanently deletes a Vector Store from OpenAI.
        Used when an Arena is deleted to prevent orphaned resources and costs.
        """
        if not vector_store_id:
            return False

        try:
            logger.info(f"Deleting OpenAI Vector Store: {vector_store_id}")
            deleted = self.client.vector_stores.delete(vector_store_id)
            return deleted.deleted
        except Exception as e:
            logger.error(f"Failed to delete vector store {vector_store_id}: {e}")
            return False

# Singleton instance
vector_store_manager = VectorStoreManager()