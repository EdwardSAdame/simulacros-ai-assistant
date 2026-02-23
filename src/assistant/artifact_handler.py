# src/assistant/artifact_handler.py
import logging
import os
from typing import List, Dict, Any
from src.services.storage_service import storage_service
from src.schemas.quiz_schemas import QuizResponse

logger = logging.getLogger(__name__)

def get_files_client(client):
    """Locates the container files accessor in the OpenAI client."""
    if hasattr(client, "beta"):
        if hasattr(client.beta, "containers") and hasattr(client.beta.containers, "files"):
            return getattr(client.beta.containers, "files")
        if hasattr(client.beta, "container_files"):
            return getattr(client.beta, "container_files")
    if hasattr(client, "containers") and hasattr(client.containers, "files"):
        return getattr(client.containers, "files")
    return getattr(client, "container_files", None)

def process_file(cf_client, container_id, file_id, filename, url_dict: Dict[str, str], folder: str):
    """Downloads content from OpenAI, uploads to AWS S3, and stores in dict by filename."""
    try:
        file_content = None
        if hasattr(cf_client, "content") and hasattr(cf_client.content, "retrieve"):
            try:
                if container_id: 
                    file_content = cf_client.content.retrieve(container_id=container_id, file_id=file_id)
                else: 
                    file_content = cf_client.content.retrieve(file_id=file_id)
            except Exception: 
                pass
            
        if file_content is None and callable(getattr(cf_client, "content", None)):
            try: 
                file_content = cf_client.content(file_id)
            except Exception: 
                pass

        if not file_content: 
            return

        # Normalize content to bytes
        if hasattr(file_content, "read"): 
            file_content = file_content.read()
        elif hasattr(file_content, "content"): 
            file_content = file_content.content
        elif hasattr(file_content, "text"): 
            file_content = file_content.text.encode('utf-8')

        if not isinstance(file_content, (bytes, bytearray)):
            try: 
                file_content = bytes(file_content)
            except Exception: 
                pass

        fname = str(filename).lower()
        if fname.endswith(".jpg") or fname.endswith(".jpeg"): 
            ctype = "image/jpeg"
        elif fname.endswith(".pdf"): 
            ctype = "application/pdf"
        else: 
            ctype = "image/png"
            if not fname.endswith(".png"): 
                filename = f"{filename}.png"
                fname = filename.lower()

        # Upload using the existing storage service
        s3_url = storage_service.upload_image_from_bytes(file_content, ctype, folder=folder)
        logger.info(f"✅ Asset uploaded to S3: {s3_url} (Mapped to {fname})")
        
        # Add to dictionary
        url_dict[fname] = s3_url
        
    except Exception as e:
        logger.error(f"File transfer failed for {file_id}: {e}")

def handle_generated_files(client, response_obj, folder: str = "chat_assets") -> Dict[str, str]:
    """Scans the OpenAI response for generated files and uploads them. Returns a dict mapping filenames to URLs."""
    uploaded_urls_map = {}
    container_id = None
    
    cf_client = get_files_client(client)
    if not cf_client: 
        return {}

    try:
        output_items = getattr(response_obj, "output", []) or []
        for item in output_items:
            item_type = getattr(item, "type", "")
            
            # Detect Container ID
            if item_type == "code_interpreter_call":
                cid = getattr(item, "container_id", None)
                if not cid and hasattr(item, "code_interpreter"):
                    cid = getattr(item.code_interpreter, "container_id", None)
                if not cid and hasattr(item, "code_interpreter_call"):
                    cid = getattr(item.code_interpreter_call, "container_id", None)
                if cid: 
                    container_id = cid

            # Detect Files in Messages
            if item_type == "message":
                content_list = getattr(item, "content", []) or []
                if isinstance(content_list, list):
                    for part in content_list:
                        annotations = getattr(part, "annotations", []) or []
                        for ann in annotations:
                            if getattr(ann, "type", "") == "container_file_citation":
                                file_id = getattr(ann, "file_id", None)
                                fname = getattr(ann, "filename", "graph.png")
                                if file_id: 
                                    process_file(cf_client, container_id, file_id, fname, uploaded_urls_map, folder)

        # Fallback: List files in container if no direct citations found but container exists
        if not uploaded_urls_map and container_id:
            try:
                container_files = cf_client.list(container_id)
                
                # 🟢 FIX: Convert to list and explicitly REVERSE it (from LIFO to FIFO)
                c_files_list = list(container_files)
                c_files_list.reverse() # Reverses the OpenAI LIFO order so Graph 1 is at index 0
                
                # Optional: apply stable sort just in case timestamps are actually different
                try:
                    c_files_list.sort(key=lambda x: getattr(x, "created_at", 0))
                except Exception:
                    pass

                for idx, c_file in enumerate(c_files_list):
                    fname = getattr(c_file, "filename", None) or getattr(c_file, "name", None)
                    fid = getattr(c_file, "id", None) or getattr(c_file, "file_id", None)
                    
                    if not fname: 
                        fname = f"graph_{idx+1}.png"
                    
                    if fname in uploaded_urls_map:
                        fname = f"generated_{fid}.png"

                    if fid: 
                        process_file(cf_client, container_id, fid, fname, uploaded_urls_map, folder)
            except Exception: 
                pass
    except Exception: 
        pass
    
    return uploaded_urls_map

def assign_urls_to_quiz(quiz_data: QuizResponse, urls_map: Dict[str, str] | List[str]):
    """Maps generated image URLs to quiz questions based on matching filenames."""
    if not urls_map: 
        return
        
    if isinstance(urls_map, list):
        urls_map = {f"graph_{i+1}.png": url for i, url in enumerate(urls_map)}

    fallback_urls = list(urls_map.values())
    fallback_idx = 0

    for q in quiz_data.questions:
        if not q.image_url:
            continue
            
        if q.image_url == "PENDING_UPLOAD" or "/mnt/" in q.image_url:
            target_filename = os.path.basename(q.image_url).lower()
            
            if target_filename in urls_map:
                q.image_url = urls_map[target_filename]
                logger.info(f"✅ Matched exactly: {target_filename} -> {q.image_url}")
            elif fallback_idx < len(fallback_urls):
                q.image_url = fallback_urls[fallback_idx]
                logger.warning(f"⚠️ Exact match failed for {target_filename}. Using fallback URL.")
                fallback_idx += 1