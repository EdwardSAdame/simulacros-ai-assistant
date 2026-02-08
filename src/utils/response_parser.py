# src/utils/response_parser.py
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

def extract_sources(response_obj: Any) -> List[Dict[str, str]]:
    """
    Parses the OpenAI response object to find URL citations.
    """
    sources = []
    try:
        output_items = getattr(response_obj, "output", []) or []
        for item in output_items:
            if getattr(item, "type", "") == "message":
                content_list = getattr(item, "content", []) or []
                for part in content_list:
                    annotations = getattr(part, "annotations", []) or []
                    for ann in annotations:
                        if getattr(ann, "type", "") == "url_citation":
                            url = getattr(ann, "url", None)
                            title = getattr(ann, "title", "Fuente")
                            if url: 
                                sources.append({"title": title, "url": url})
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