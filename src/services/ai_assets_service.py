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
        Scans the OpenAI response for explicit file outputs, uploads them,
        and returns a map: { 'filename.png': 's3_url' }.
        """
        uploaded_map = {} 
        processed_file_ids = set()
        container_id = None
        explicit_files_to_process = [] 
        
        cf_client = AiAssetsService._get_files_client(client)
        if not cf_client: return {}

        try:
            output_items = getattr(response_obj, "output", []) or []
            for item in output_items:
                item_type = getattr(item, "type", "")
                
                # 1. Detect Container ID & Explicit Image Outputs (plt.show())
                if item_type == "code_interpreter_call":
                    cid = getattr(item, "container_id", None) or \
                          (getattr(item.code_interpreter, "container_id", None) if hasattr(item, "code_interpreter") else None) or \
                          (getattr(item.code_interpreter_call, "container_id", None) if hasattr(item, "code_interpreter_call") else None)
                    if cid: container_id = cid
                    
                    # FIX: Add 'or []' to prevent NoneType iteration errors
                    outputs = getattr(item, "outputs", []) or []
                    if not outputs and hasattr(item, "code_interpreter"):
                        outputs = getattr(item.code_interpreter, "outputs", []) or []
                    if not outputs and hasattr(item, "code_interpreter_call"):
                        outputs = getattr(item.code_interpreter_call, "outputs", []) or []
                        
                    outputs = outputs or [] # Final safety net
                        
                    for out in outputs:
                        if getattr(out, "type", "") == "image":
                            image_obj = getattr(out, "image", None)
                            if image_obj:
                                f_id = getattr(image_obj, "file_id", None)
                                if f_id:
                                    explicit_files_to_process.append((f_id, f"plot_output_{f_id}.png"))

                # 2. Detect citations from messages (saved files via file system)
                if item_type == "message":
                    content_list = getattr(item, "content", []) or []
                    if isinstance(content_list, list):
                        for part in content_list:
                            annotations = getattr(part, "annotations", []) or []
                            for ann in annotations:
                                if getattr(ann, "type", "") == "container_file_citation":
                                    if not container_id:
                                        container_id = getattr(ann, "container_id", None)
                                    f_id = getattr(ann, "file_id", None)
                                    f_name = getattr(ann, "filename", f"file_{f_id}.png")
                                    if f_id:
                                        explicit_files_to_process.append((f_id, f_name))

            # 3. Process explicit files ONLY (Protects against reused container ghost files)
            if explicit_files_to_process:
                for f_id, f_name in explicit_files_to_process:
                    if f_id not in processed_file_ids:
                        s3_url = AiAssetsService._process_file(cf_client, container_id, f_id, f_name, folder)
                        if s3_url:
                            uploaded_map[f_name] = s3_url
                            processed_file_ids.add(f_id)
            else:
                # 4. Fallback: List ALL files ONLY if absolutely nothing was found explicitly
                if container_id:
                    try:
                        container_files = cf_client.list(container_id)
                        all_files = [f for f in container_files]
                        all_files.reverse() 
                        all_files.sort(key=lambda f: getattr(f, "created_at", 0))

                        for c_file in all_files:
                            fid = getattr(c_file, "id", None) or getattr(c_file, "file_id", None)
                            raw_fname = getattr(c_file, "filename", None) or getattr(c_file, "name", None) or "plot.png"
                            
                            fname = raw_fname
                            counter = 1
                            while fname in uploaded_map:
                                name_part, ext_part = os.path.splitext(raw_fname)
                                fname = f"{name_part}_{counter}{ext_part}"
                                counter += 1
                            
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
            if hasattr(cf_client, "content") and hasattr(cf_client.content, "retrieve"):
                try:
                    if container_id: file_content = cf_client.content.retrieve(container_id=container_id, file_id=file_id)
                    else: file_content = cf_client.content.retrieve(file_id=file_id)
                except: pass
            
            if file_content is None and callable(getattr(cf_client, "content", None)):
                try: file_content = cf_client.content(file_id)
                except: pass

            if not file_content: return None

            if hasattr(file_content, "read"): file_content = file_content.read()
            elif hasattr(file_content, "content"): file_content = file_content.content
            elif hasattr(file_content, "text"): file_content = file_content.text.encode('utf-8')

            if not isinstance(file_content, (bytes, bytearray)):
                try: file_content = bytes(file_content)
                except: pass

            fname = str(filename).lower()
            if fname.endswith(".jpg") or fname.endswith(".jpeg"): ctype = "image/jpeg"
            elif fname.endswith(".pdf"): ctype = "application/pdf"
            else: 
                ctype = "image/png"
                if not fname.endswith(".png"): filename = f"{filename}.png"

            s3_url = storage_service.upload_image_from_bytes(file_content, ctype, folder=folder)
            logger.info(f"✅ Asset uploaded to S3: {s3_url}")
            return s3_url
        except Exception as e:
            logger.error(f"File transfer failed for {file_id}: {e}")
            return None

ai_assets_service = AiAssetsService()