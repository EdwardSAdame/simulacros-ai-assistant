# src/services/creative_image_service.py
import logging
import base64
from typing import Any, Dict, List, Tuple

from src.assistant.assistant_client import stream_chat_response
from src.utils.image_stream_parser import ImageStreamParser
from src.services.storage_service import storage_service

# NEW IMPORTS: Bring in the prompt builders
from src.services.context_builder import build_runtime_context
from src.config.system_instructions import build_system_instructions

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
    ) -> Tuple[str, List[str], Dict[str, Any]]: # 🟢 FIX: Updated Type Hint
        """
        Triggers the image generation stream and dispatches partial/final 
        images via WebSockets.
        
        Returns:
            Tuple containing the final text response, a list of final S3 image URLs, and token usage.
        """
        logger.info(f"Starting creative image stream for user {user_id}")
        
        final_text = ""
        final_image_urls = []
        final_usage = {} # 🟢 FIX: Variable to hold the tokens for the orchestrator

        try:
            # 1. Build Runtime Signals
            runtime_signals = build_runtime_context(
                page=page,
                user_id=user_id,
                name=name,
                email=email,
                requires_visuals=False
            )
            
            # 2. Build System Prompt with the Creative Image Doctrine active
            system_prompt = build_system_instructions(
                extras=runtime_signals,
                requires_creative_image=True # This safely injects the Monet rules!
            )

            # 3. Trigger the stream using the updated assistant client
            raw_stream = stream_chat_response(
                conversation_input=conversation_input,
                user_id=user_id,
                page=page,
                name=name,
                email=email,
                mode=mode,
                enable_image_generation=True,
                system_instruction=system_prompt # Passing the correctly built prompt
            )
            
            # 4. Parse the stream and dispatch events to the frontend
            for event in ImageStreamParser.parse(raw_stream):
                evt_type = event.get("type")
                
                if evt_type == "status":
                    if stream_manager:
                        stream_manager.send_status(event.get("message", "Processing image..."))
                
                elif evt_type == "partial_image":
                    b64_data = event.get("b64_data", "")
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
                                b64_data=s3_url  
                            )
                    except Exception as upload_err:
                        logger.warning(f"Partial image S3 upload failed: {upload_err}")
                    
                elif evt_type == "final_image":
                    b64_data = event.get("b64_data", "")
                    revised_prompt = event.get("revised_prompt", "")
                    
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
                                b64_data=final_s3_url, 
                                revised_prompt=revised_prompt
                            )
                    except Exception as upload_err:
                        logger.error(f"Final image S3 upload failed: {upload_err}")
                        
                elif evt_type == "text":
                    final_text += event.get("text", "")
                    
                # 🟢 FIX: Intercept Usage Metrics and send to frontend
                elif evt_type == "usage_metrics":
                    final_usage = event.get("data", {}) # Store to return it to orchestrator
                    logger.info(f"Image generation usage metrics captured: {final_usage}")
                    if stream_manager and final_usage:
                        stream_manager.send_usage_metrics(final_usage)
                    
                elif evt_type == "error":
                    error_msg = event.get("error", "Unknown error generating image.")
                    logger.error(f"Image generation stream error: {error_msg}")
                    if stream_manager:
                        stream_manager.send_error(error_msg)
                    return "**Error**: We could not generate the image.", [], {}

            # Clean safety net fallback (leaves text empty if AI fails to generate a description)
            if not final_text.strip() and final_image_urls:
                final_text = ""

            # 🟢 FIX: Return exactly 3 items to match what orchestrator_service.py expects
            return final_text, final_image_urls, final_usage
            
        except Exception as e:
            logger.error(f"Failed to execute creative image service: {e}")
            if stream_manager:
                stream_manager.send_error("Failed to connect to the image engine.")
            return "**Error**: Image generation failed due to a server error.", [], {}