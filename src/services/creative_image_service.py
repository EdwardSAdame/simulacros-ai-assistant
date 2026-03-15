# src/services/creative_image_service.py
import logging
import base64
from typing import Any, Dict, List, Tuple

from src.assistant.assistant_client import stream_chat_response
from src.utils.image_stream_parser import ImageStreamParser
from src.services.storage_service import storage_service  # 🟢 Import your S3 logic

logger = logging.getLogger(__name__)

class CreativeImageService:
    """
    Service responsible for handling creative image generation requests.
    It isolates the streaming logic for OpenAI's Responses API image generation tool.
    """

    @staticmethod
    def generate_image(
        conversation_input: List[Dict[str, Any]],
        user_id: str | None,
        page: str | None,
        name: str | None,
        email: str | None,
        mode: str,
        stream_manager: Any
    ) -> Tuple[str, List[str]]:
        """
        Triggers the image generation stream and dispatches partial/final 
        images via WebSockets.
        
        Returns:
            Tuple containing the final text response and a list of final S3 image URLs.
        """
        logger.info(f"Starting creative image stream for user {user_id}")
        
        final_text = ""
        final_image_urls = []

        try:
            # 1. Trigger the stream using the updated assistant client
            raw_stream = stream_chat_response(
                conversation_input=conversation_input,
                user_id=user_id,
                page=page,
                name=name,
                email=email,
                mode=mode,
                enable_image_generation=True 
            )
            
            # 2. Parse the stream and dispatch events to the frontend
            for event in ImageStreamParser.parse(raw_stream):
                evt_type = event.get("type")
                
                if evt_type == "status":
                    if stream_manager:
                        stream_manager.send_status(event.get("message", "Processing image..."))
                
                elif evt_type == "partial_image":
                    b64_data = event.get("b64_data", "")
                    # 🟢 FIX: Decode Base64 to bytes and upload to S3
                    try:
                        image_bytes = base64.b64decode(b64_data)
                        s3_url = storage_service.upload_image_from_bytes(
                            image_bytes, 
                            "image/png", 
                            folder="chat_assets"
                        )
                        
                        if stream_manager:
                            stream_manager.send_partial_image(
                                index=event.get("index", 0),
                                b64_data=s3_url  # Now sending the URL, not the massive string!
                            )
                    except Exception as upload_err:
                        logger.warning(f"Partial image S3 upload failed: {upload_err}")
                    
                elif evt_type == "final_image":
                    b64_data = event.get("b64_data", "")
                    revised_prompt = event.get("revised_prompt", "")
                    
                    # 🟢 FIX: Decode Final Base64 to bytes and upload to S3
                    try:
                        image_bytes = base64.b64decode(b64_data)
                        final_s3_url = storage_service.upload_image_from_bytes(
                            image_bytes, 
                            "image/png", 
                            folder="chat_assets"
                        )
                        final_image_urls.append(final_s3_url)
                        
                        if stream_manager:
                            stream_manager.send_final_image(
                                b64_data=final_s3_url, # Sending the URL
                                revised_prompt=revised_prompt
                            )
                    except Exception as upload_err:
                        logger.error(f"Final image S3 upload failed: {upload_err}")
                        
                elif evt_type == "text":
                    final_text += event.get("text", "")
                    
                elif evt_type == "error":
                    error_msg = event.get("error", "Unknown error generating image.")
                    logger.error(f"Image generation stream error: {error_msg}")
                    if stream_manager:
                        stream_manager.send_error(error_msg)
                    return "**Error**: We could not generate the image.", []

            if not final_text.strip() and final_image_urls:
                # 🟢 RETURN EMPTY STRING INSTEAD OF HARDCODED ENGLISH FALLBACK
                final_text = ""

            return final_text, final_image_urls
            
        except Exception as e:
            logger.error(f"Failed to execute creative image service: {e}")
            if stream_manager:
                stream_manager.send_error("Failed to connect to the image engine.")
            return "**Error**: Image generation failed due to a server error.", []