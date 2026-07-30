# Backend: simulacros-ai-assistant
# File: src/utils/response_parser.py

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def is_valid_image_url(url: str) -> bool:
    """Returns True if the URL looks like a supported image format."""
    if not url or not isinstance(url, str):
        return False
    if url.startswith("wix:image"): 
        return True 
    clean = url.lower().split('?')[0]
    return clean.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))

def extract_sources(response_obj: Any, arena_files: List[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """
    Parses the OpenAI response object to find URL citations and File citations.
    Maps file citations into a pseudo-URL format compatible with the frontend renderer.
    Cross-references hashed filenames against arena_files to restore original human-readable names.
    """
    sources = []
    arena_files = arena_files or []
    
    try:
        output_items = getattr(response_obj, "output", []) or []
        for item in output_items:
            if getattr(item, "type", "") == "message":
                content_list = getattr(item, "content", []) or []
                for part in content_list:
                    annotations = getattr(part, "annotations", []) or []
                    for ann in annotations:
                        ann_type = getattr(ann, "type", "")
                        
                        # Handle standard web search citations
                        if ann_type == "url_citation":
                            url = getattr(ann, "url", None)
                            title = getattr(ann, "title", "Fuente Web")
                            if url: 
                                sources.append({"title": title, "url": url})
                                
                        # Handle vector store file citations
                        elif ann_type == "file_citation":
                            # Depending on the SDK version, properties may be nested or flat
                            file_citation_obj = getattr(ann, "file_citation", ann)
                            file_id = getattr(file_citation_obj, "file_id", "unknown_id")
                            hashed_filename = getattr(file_citation_obj, "filename", "Documento de Arena")
                            
                            # Matchmake: Find original name using the hashed filename
                            display_name = hashed_filename
                            for file_data in arena_files:
                                file_url = file_data.get("url", "")
                                # If the hashed filename from OpenAI is part of the original CDN URL
                                if hashed_filename in file_url:
                                    display_name = file_data.get("name", hashed_filename)
                                    break
                            
                            # Construct a pseudo-URL to satisfy the frontend URL parser
                            pseudo_url = f"https://documento.arena/archivo/{file_id}"
                            sources.append({"title": display_name, "url": pseudo_url})
                            
    except Exception as e:
        logger.error(f"Error extracting sources: {e}")
    
    # Deduplicate based on URL
    unique_sources = []
    seen_urls = set()
    for s in sources:
        if s["url"] not in seen_urls:
            unique_sources.append(s)
            seen_urls.add(s["url"])
            
    return unique_sources