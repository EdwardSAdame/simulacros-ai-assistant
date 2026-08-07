# src/assistant/vector_store_manager.py
import logging
import requests
from io import BytesIO
from typing import List, Optional, Tuple, Dict, Set, Union
from src.config.settings import get_openai_client

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    Handles interactions with OpenAI File Search Vector Store API.
    Responsible for creating stores, uploading files, and managing the lifecycle.
    """

    def __init__(self):
        self.client = get_openai_client()

    def _get_filename(self, url: str, name: Optional[str] = None) -> str:
        """
        Normalizes and derives a consistent filename from a URL or explicit name.
        """
        if name and isinstance(name, str) and name.strip():
            clean_name = name.strip().split("?")[0]
            if clean_name:
                return clean_name

        if url and isinstance(url, str):
            clean_url = url.split("?")[0]
            filename = clean_url.split("/")[-1]
            if filename:
                return filename

        return "document.pdf"

    def _download_file_content(self, url: str, name: Optional[str] = None) -> Optional[Tuple[str, BytesIO]]:
        """
        Downloads a file from a URL into a memory buffer for OpenAI upload.
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            filename = self._get_filename(url, name)

            return (filename, BytesIO(response.content))
        except Exception as e:
            logger.error(f"Failed to download file from {url}: {e}")
            return None

    def create_arena_knowledge_base(
        self, 
        arena_name: str, 
        files: List[Union[str, Dict[str, str]]]
    ) -> Optional[str]:
        """
        Creates a Vector Store for an Arena and processes the initial files.
        Returns the vector_store_id.
        """
        if not files:
            return None

        try:
            logger.info(f"Creating Vector Store for Arena: {arena_name}")

            vector_store = self.client.vector_stores.create(
                name=f"Arena: {arena_name}"
            )

            valid_streams = []

            for item in files:
                if isinstance(item, dict):
                    url = item.get("url")
                    name = item.get("name")
                else:
                    url = item
                    name = None

                if url:
                    file_data = self._download_file_content(url, name)
                    if file_data:
                        valid_streams.append(file_data)

            if not valid_streams:
                logger.warning("No valid files could be downloaded for Arena creation.")
                return vector_store.id

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

    def add_files_to_arena(
        self, 
        vector_store_id: str, 
        files: List[Union[str, Dict[str, str]]]
    ):
        """
        Adds new files to an existing Vector Store.
        """
        if not vector_store_id or not files:
            return

        try:
            valid_streams = []
            for item in files:
                if isinstance(item, dict):
                    url = item.get("url")
                    name = item.get("name")
                else:
                    url = item
                    name = None

                if url:
                    file_data = self._download_file_content(url, name)
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

    def sync_arena_files(self, vector_store_id: str, new_files: List[Dict[str, str]]):
        """
        Synchronizes the Vector Store with the provided list of files.
        Deletes files that are no longer in new_files.
        Uploads files that are new.
        """
        if not vector_store_id:
            return

        try:
            logger.info(f"Syncing files for Vector Store: {vector_store_id}")

            openai_files = self.client.vector_stores.files.list(
                vector_store_id=vector_store_id,
                limit=100
            )

            existing_file_map = {}
            for f in openai_files.data:
                try:
                    file_details = self.client.files.retrieve(f.id)
                    existing_file_map[file_details.filename] = f.id
                except Exception:
                    continue

            new_filenames = set()
            items_to_upload = []

            for nf in new_files:
                url = nf.get("url")
                name = nf.get("name")

                if not url:
                    continue

                filename = self._get_filename(url, name)
                new_filenames.add(filename)

                if filename not in existing_file_map:
                    items_to_upload.append(nf)

            files_to_delete_ids = []
            for existing_name, existing_id in existing_file_map.items():
                if existing_name not in new_filenames:
                    files_to_delete_ids.append(existing_id)

            if files_to_delete_ids:
                logger.info(f"Deleting {len(files_to_delete_ids)} removed files from Vector Store...")
                for fid in files_to_delete_ids:
                    try:
                        self.client.vector_stores.files.delete(
                            vector_store_id=vector_store_id,
                            file_id=fid
                        )
                    except Exception as e:
                        logger.warning(f"Failed to delete file {fid}: {e}")

            if items_to_upload:
                logger.info(f"Uploading {len(items_to_upload)} new files to Vector Store...")
                self.add_files_to_arena(vector_store_id, items_to_upload)

            logger.info("Vector Store Sync Complete.")

        except Exception as e:
            logger.error(f"Error syncing Vector Store: {e}", exc_info=True)

    def delete_vector_store(self, vector_store_id: str) -> bool:
        """
        Permanently deletes a Vector Store from OpenAI.
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


vector_store_manager = VectorStoreManager()