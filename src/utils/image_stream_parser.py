# src/utils/image_stream_parser.py
import logging
from typing import Any, Dict, Generator

logger = logging.getLogger(__name__)

class ImageStreamParser:
    """
    Parses the raw stream from OpenAI's Responses API when generating images.
    Extracts partial images, the final image, and any conversational text.
    """

    @staticmethod
    def parse(stream: Any) -> Generator[Dict[str, Any], None, None]:
        """
        Iterates over the OpenAI stream and yields normalized dictionaries.
        """
        try:
            for event in stream:
                # The OpenAI Python SDK usually returns objects, so we use getattr.
                event_type = getattr(event, "type", "")

                # 1. Handle Partial Images
                if event_type == "response.image_generation_call.partial_image":
                    yield {
                        "type": "partial_image",
                        "index": getattr(event, "partial_image_index", 0),
                        "b64_data": getattr(event, "partial_image_b64", "")
                    }

                # 2. Handle Final Image Completion
                elif event_type == "response.output_item.done":
                    item = getattr(event, "item", None)
                    if item:
                        item_type = getattr(item, "type", "")
                        
                        # Check if the completed item was the image
                        if item_type == "image_generation_call":
                            yield {
                                "type": "final_image",
                                "b64_data": getattr(item, "result", ""),
                                "revised_prompt": getattr(item, "revised_prompt", "")
                            }
                        
                        # Sometimes the text comes as a completed message item at the very end
                        elif item_type == "message":
                            content_blocks = getattr(item, "content", [])
                            for block in content_blocks:
                                if getattr(block, "type", "") == "text":
                                    yield {
                                        "type": "text",
                                        "text": getattr(block, "text", "")
                                    }

                # 3. Handle Conversational Text Deltas (During streaming)
                # OpenAI uses "response.message.content_part.delta" for standard text streaming
                elif event_type == "response.message.content_part.delta":
                    delta = getattr(event, "delta", None)
                    if delta and getattr(delta, "type", "") == "text":
                        yield {
                            "type": "text",
                            "text": getattr(delta, "text", "")
                        }
                        
                # Keep legacy check just in case
                elif event_type == "response.output_item.content.delta":
                    delta = getattr(event, "delta", None)
                    if delta and getattr(delta, "type", "") == "text":
                        yield {
                            "type": "text",
                            "text": getattr(delta, "text", "")
                        }

        except Exception as e:
            logger.error(f"Error parsing image stream: {e}")
            yield {"type": "error", "error": str(e)}