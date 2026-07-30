# Backend: simulacros-ai-assistant
# File: src/utils/response_parser.py

import logging
import urllib.parse
import re
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

def clean_text_citations(text: str) -> str:
    """
    Replaces raw OpenAI annotation markers like 【13†source】 with clean sequential citation numbers [1], [2], etc.
    """
    if not text:
        return ""
    
    # Find all unique citation markers in the text
    markers = re.findall(r'【\d+†[^】]+】', text)
    unique_markers = list(dict.fromkeys(markers))
    
    cleaned_text = text
    for index, marker in enumerate(unique_markers, start=1):
        cleaned_text = cleaned_text.replace(marker, f"[{index}]")
        
    return cleaned_text

def extract_sources(response_obj: Any, arena_files: List[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """
    Parses the OpenAI response object to find URL citations and File citations.
    Maps file citations to their real Wix CDN URL stored in DynamoDB.
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
                            
                            # Matchmake: Find original name and real URL by parsing the Wix URL
                            display_name = hashed_filename
                            real_url = f"https://documento.arena/archivo/{file_id}" # Fallback pseudo-URL
                            
                            for file_data in arena_files:
                                file_url = file_data.get("url", "")
                                
                                # If the hashed filename from OpenAI is part of the original CDN URL
                                if hashed_filename in file_url:
                                    # Override fallback with the real URL from DynamoDB
                                    real_url = file_url
                                    
                                    # Extract the real filename from the end of the Wix URL
                                    url_parts = file_url.split("/")
                                    extracted_name = url_parts[-1] if url_parts else ""
                                    
                                    if extracted_name and extracted_name != hashed_filename:
                                        # Decode URL-encoded characters (e.g., %20 to space)
                                        display_name = urllib.parse.unquote(extracted_name)
                                    else:
                                        # Fallback to the 'name' attribute or the hashed name
                                        display_name = file_data.get("name", hashed_filename)
                                    break
                            
                            sources.append({"title": display_name, "url": real_url})
                            
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