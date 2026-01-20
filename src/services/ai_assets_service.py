# src/services/ai_assets_service.py
import logging
import os  # 🟢 NEW IMPORT
from typing import Dict, List, Any # 🟢 CHANGED TYPE
from src.services.storage_service import storage_service

logger = logging.getLogger(__name__)

class AiAssetsService:
    
    # 🟢 CHANGED: Return Type is now Dict[str, str] (Filename -> S3 URL)
    @staticmethod
    def handle_generated_files(client, response_obj, folder: str = "chat_assets") -> Dict[str, str]:
        """Scans the OpenAI response, uploads files, and returns a map of {filename: s3_url}."""
        uploaded_map = {}  # 🟢 CHANGED: Dictionary instead of list
        container_id = None
        
        cf_client = AiAssetsService._get_files_client(client)
        if not cf_client: return {}

        try:
            output_items = getattr(response_obj, "output", []) or []
            # ... (Lógica de detección de container_id igual que antes) ...
            for item in output_items:
                item_type = getattr(item, "type", "")
                if item_type == "code_interpreter_call":
                    cid = getattr(item, "container_id", None) or \
                          (getattr(item.code_interpreter, "container_id", None) if hasattr(item, "code_interpreter") else None) or \
                          (getattr(item.code_interpreter_call, "container_id", None) if hasattr(item, "code_interpreter_call") else None)
                    if cid: container_id = cid

            # Fallback: List files in container (La parte crítica)
            if container_id:
                try:
                    container_files = cf_client.list(container_id)
                    all_files = [f for f in container_files]
                    
                    # 🔴 REMOVED: Ya no necesitamos el sort inestable.
                    
                    for c_file in all_files:
                        fname = getattr(c_file, "filename", None) or getattr(c_file, "name", None)
                        fid = getattr(c_file, "id", None) or getattr(c_file, "file_id", None)
                        
                        if not fname: fname = "generated_plot.png"
                        
                        if fid: 
                            # Procesamos y guardamos en el mapa
                            s3_url = AiAssetsService._process_file(cf_client, container_id, fid, fname, folder)
                            if s3_url:
                                uploaded_map[fname] = s3_url # 🟢 Mapeo exacto
                                
                except Exception as e:
                    logger.warning(f"Failed to list container files: {e}")

        except Exception as e:
            logger.error(f"Error handling generated files: {e}")
            
        return uploaded_map

    # ... ( _get_files_client sigue igual ) ...

    @staticmethod
    def _process_file(cf_client, container_id, file_id, filename, folder: str) -> str | None:
        """Downloads content and uploads to S3. Returns single URL or None."""
        try:
            # ... (Lógica de recuperación de file_content sigue igual) ...
            file_content = None
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
            fname_clean = str(filename).lower()
            if fname_clean.endswith(".jpg") or fname_clean.endswith(".jpeg"): ctype = "image/jpeg"
            elif fname_clean.endswith(".pdf"): ctype = "application/pdf"
            else: 
                ctype = "image/png"
                if not fname_clean.endswith(".png"): filename = f"{filename}.png"

            # Upload
            s3_url = storage_service.upload_image_from_bytes(file_content, ctype, folder=folder)
            logger.info(f"✅ Asset uploaded to S3: {filename} -> {s3_url}")
            
            return s3_url # 🟢 Return URL directly

        except Exception as e:
            logger.error(f"File transfer failed for {file_id}: {e}")
            return None