# src/assistant/image_handler.py
from typing import List, Dict, Any

def format_image_urls_for_openai(image_urls: List[str]) -> List[Dict[str, Any]]:
    """
    Formats image URLs into OpenAI-compatible content blocks.
    Validates input to prevent null or malformed URLs from breaking the API payload.
    """
    if not image_urls:
        return []

    content_parts = []
    
    for url in image_urls:
        if not url or not isinstance(url, str):
            continue
            
        content_parts.append({
            "type": "input_image",
            "image_url": url.strip()
        })

    return content_parts