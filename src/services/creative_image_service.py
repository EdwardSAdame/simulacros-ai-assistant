# src/services/creative_image_service.py
import logging
from typing import Any, Dict, List, Tuple

from src.assistant.assistant_client import stream_chat_response
from src.utils.image_stream_parser import ImageStreamParser

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
            Tuple containing the final text response and a list of final base64 images.
        """
        logger.info(f"Starting creative image stream for user {user_id}")
        
        final_text = ""
        final_images_b64 = []

        try:
            # 1. Trigger the stream using the updated assistant client
            # The enable_image_generation flag ensures the Claude Monet instruction is injected
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
                    if stream_manager:
                        stream_manager.send_partial_image(
                            index=event.get("index", 0),
                            b64_data=event.get("b64_data", "")
                        )
                    
                elif evt_type == "final_image":
                    b64_data = event.get("b64_data", "")
                    revised_prompt = event.get("revised_prompt", "")
                    final_images_b64.append(b64_data)
                    
                    if stream_manager:
                        stream_manager.send_final_image(
                            b64_data=b64_data,
                            revised_prompt=revised_prompt
                        )
                        
                elif evt_type == "text":
                    # Append any conversational text the model generates alongside the image
                    final_text += event.get("text", "")
                    
                elif evt_type == "error":
                    error_msg = event.get("error", "Unknown error generating image.")
                    logger.error(f"Image generation stream error: {error_msg}")
                    if stream_manager:
                        stream_manager.send_error(error_msg)
                    return "**Error**: We could not generate the image.", []

            # Provide a fallback text if the model only returned an image with no text
            if not final_text.strip() and final_images_b64:
                final_text = "Here is your generated image."

            return final_text, final_images_b64
            
        except Exception as e:
            logger.error(f"Failed to execute creative image service: {e}")
            if stream_manager:
                stream_manager.send_error("Failed to connect to the image engine.")
            return "**Error**: Image generation failed due to a server error.", []