# src/services/ai_assets_service.py
import logging
import os
from typing import Dict, List, Any
from src.services.storage_service import storage_service

logger = logging.getLogger(__name__)

class AiAssetsService:
    """
    Handles the extraction, download, and upload of file artifacts.
    Returns a Dictionary mapping filenames to S3 URLs to ensure exact matching.
    """

    @staticmethod
    def handle_generated_files(client, response_obj, folder: str = "chat_assets") -> Dict[str, str]:
        """
        Scans the OpenAI response, lists all files in the container, uploads them,
        and returns a map: { 'filename.png': 's3_url' }.
        """
        uploaded_map = {} 
        processed_file_ids = set()
        container_id = None
        
        cf_client = AiAssetsService._get_files_client(client)
        if not cf_client: return {}

        try:
            output_items = getattr(response_obj, "output", []) or []
            for item in output_items:
                item_type = getattr(item, "type", "")
                
                # 1. Detect Container ID (from Tool Call or Message)
                if item_type == "code_interpreter_call":
                    cid = getattr(item, "container_id", None) or \
                          (getattr(item.code_interpreter, "container_id", None) if hasattr(item, "code_interpreter") else None) or \
                          (getattr(item.code_interpreter_call, "container_id", None) if hasattr(item, "code_interpreter_call") else None)
                    if cid: container_id = cid

                # 2. Detect container_id from citations if missed earlier
                if item_type == "message":
                    content_list = getattr(item, "content", []) or []
                    if isinstance(content_list, list):
                        for part in content_list:
                            annotations = getattr(part, "annotations", []) or []
                            for ann in annotations:
                                if getattr(ann, "type", "") == "container_file_citation":
                                    if not container_id:
                                        container_id = getattr(ann, "container_id", None)

            # 3. List ALL files in the container and map them by Name
            if container_id:
                try:
                    container_files = cf_client.list(container_id)
                    all_files = [f for f in container_files]
                    
                    # Note: We don't strictly need to sort here because we are using a Dict map,
                    # but sorting helps the Fallback mechanism (see AssistantClient) behave predictably.
                    all_files.sort(key=lambda f: getattr(f, "created_at", 0))

                    for c_file in all_files:
                        fid = getattr(c_file, "id", None) or getattr(c_file, "file_id", None)
                        fname = getattr(c_file, "filename", None) or getattr(c_file, "name", None) or "plot.png"
                        
                        if fid and fid not in processed_file_ids: 
                            s3_url = AiAssetsService._process_file(cf_client, container_id, fid, fname, folder)
                            if s3_url:
                                uploaded_map[fname] = s3_url
                                processed_file_ids.add(fid)
                            
                except Exception as e:
                    logger.warning(f"Failed to list container files: {e}")

        except Exception as e:
            logger.error(f"Error handling generated files: {e}")
            
        return uploaded_map

    @staticmethod
    def _get_files_client(client):
        """Locates the container files accessor in the OpenAI client."""
        if hasattr(client, "beta"):
            if hasattr(client.beta, "containers") and hasattr(client.beta.containers, "files"):
                return getattr(client.beta.containers, "files")
            if hasattr(client.beta, "container_files"):
                return getattr(client.beta, "container_files")
        if hasattr(client, "containers") and hasattr(client.containers, "files"):
            return getattr(client.containers, "files")
        return getattr(client, "container_files", None)

    @staticmethod
    def _process_file(cf_client, container_id, file_id, filename, folder: str) -> str | None:
        """Downloads content from OpenAI and uploads to AWS S3."""
        try:
            file_content = None
            # Attempt retrieval
            if hasattr(cf_client, "content") and hasattr(cf_client.content, "retrieve"):
                try:
                    if container_id: file_content = cf_client.content.retrieve(container_id=container_id, file_id=file_id)
                    else: file_content = cf_client.content.retrieve(file_id=file_id)
                except: pass
            
            # Fallback retrieval style
            if file_content is None and callable(getattr(cf_client, "content", None)):
                try: file_content = cf_client.content(file_id)
                except: pass

            if not file_content: return None

            # Extract bytes
            if hasattr(file_content, "read"): file_content = file_content.read()
            elif hasattr(file_content, "content"): file_content = file_content.content
            elif hasattr(file_content, "text"): file_content = file_content.text.encode('utf-8')

            if not isinstance(file_content, (bytes, bytearray)):
                try: file_content = bytes(file_content)
                except: pass

            # Determine Content Type
            fname = str(filename).lower()
            if fname.endswith(".jpg") or fname.endswith(".jpeg"): ctype = "image/jpeg"
            elif fname.endswith(".pdf"): ctype = "application/pdf"
            else: 
                ctype = "image/png"
                if not fname.endswith(".png"): filename = f"{filename}.png"

            # Upload
            s3_url = storage_service.upload_image_from_bytes(file_content, ctype, folder=folder)
            logger.info(f"✅ Asset uploaded to S3: {s3_url}")
            return s3_url
        except Exception as e:
            logger.error(f"File transfer failed for {file_id}: {e}")
            return None

# Expose a simple singleton
ai_assets_service = AiAssetsService()