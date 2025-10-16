def format_image_urls_for_openai(image_urls: list[str]) -> list[dict]:
    """
    Formats image URLs into OpenAI-compatible content blocks.
    """
    content_parts = []

    for url in image_urls:
        content_parts.append({
            "type": "input_image",
            "image_url": url  # Assign the URL string directly
        })

    return content_parts