def format_image_urls_for_openai(image_urls: list[str]) -> list[dict]:
    """
    Formats image URLs into OpenAI-compatible content blocks.
    """
    content_parts = []

    for url in image_urls:
        content_parts.append({
            "type": "input_image",
            "input_image": {
                "url": url
            }
        })

    return content_parts
