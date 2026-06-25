# src/services/flashcard_service.py
import logging
import threading
import base64
import random
from typing import Dict, Any, List, Tuple

from src.utils.logging_utils import log_event
from src.config.settings import get_openai_client, get_image_generation_size, get_image_generation_partials
from src.config.model_config import get_model_config
from src.services.token_usage_service import TokenUsageService
from src.services.image_usage_service import ImageUsageService
from src.services.storage_service import storage_service
from src.schemas.flashcard_schemas import FlashcardsPayload
from src.config.flashcard_instructions import get_flashcard_system_prompt
from src.config.creative_image_instructions import get_creative_image_system_prompt

from src.utils.stream_parser import StreamParser

logger = logging.getLogger(__name__)

class FlashcardsService:
    """
    Encapsulates logic for generating study flashcards.
    Utilizes OpenAI's Responses API to guarantee schema adherence and 
    uses a background thread to generate an aesthetic topic image in parallel.
    """

    @staticmethod
    def _extract_usage_from_obj(usage_obj: Any) -> Dict[str, int]:
        """Helper to safely extract token usage dictionaries from OpenAI response objects."""
        if not usage_obj:
            return {}
        if isinstance(usage_obj, dict):
            return {
                "input_tokens": usage_obj.get("input_tokens", usage_obj.get("prompt_tokens", 0)),
                "output_tokens": usage_obj.get("output_tokens", usage_obj.get("completion_tokens", 0)),
                "total_tokens": usage_obj.get("total_tokens", 0)
            }
        return {
            "input_tokens": getattr(usage_obj, "input_tokens", getattr(usage_obj, "prompt_tokens", 0)),
            "output_tokens": getattr(usage_obj, "output_tokens", getattr(usage_obj, "completion_tokens", 0)),
            "total_tokens": getattr(usage_obj, "total_tokens", 0)
        }

    @staticmethod
    def _log_usage(usage_data: Any, current_user: str | None, conversation_id: str, active_mode: str):
        if not usage_data or not current_user: 
            return
        
        try:
            active_config = get_model_config(active_mode)
            engine_name = active_config.model

            input_val = getattr(usage_data, "input_tokens", 0)
            output_val = getattr(usage_data, "output_tokens", 0)
            total_val = getattr(usage_data, "total_tokens", 0)

            TokenUsageService().log_token_usage(
                user_id=current_user,
                conversation_id=conversation_id, 
                source="flashcards",                 
                tier=active_mode,   
                engine=engine_name, 
                input_tokens=input_val,
                output_tokens=output_val,
                total_tokens=total_val
            )
        except Exception as e:
            logger.error(f"Failed to log token usage in flashcard service: {e}")

    @classmethod
    def _bg_image_worker(
        cls, 
        image_prompt: str, 
        user_id: str | None, 
        actual_conversation_id: str | None, 
        mode: str, 
        stream_manager: Any,
        result_container: Dict[str, Any]
    ):
        """
        Background worker that generates an educational illustration for the flashcard deck.
        Streams partial updates directly to the frontend to improve perceived load times.
        """
        try:
            bg_client = get_openai_client()
            active_config = get_model_config(mode)
            
            base_instruction = "You are an expert AI illustrator. Use the image_generation tool to create the requested image.\n\n"
            instructions = base_instruction + get_creative_image_system_prompt()

            bg_req = {
                "model": active_config.model,
                "input": [{"role": "user", "content": image_prompt}],
                "tools": [{
                    "type": "image_generation",
                    "model": active_config.image_model,
                    "partial_images": get_image_generation_partials(),
                    "size": get_image_generation_size(),
                    "quality": active_config.image_quality
                }],
                "instructions": instructions,
                "stream": True
            }

            bg_stream = bg_client.responses.create(**bg_req)
            final_url = None

            for bg_event in bg_stream:
                if getattr(bg_event, "type", "") == "response.completed":
                    resp_obj = getattr(bg_event, "response", bg_event)
                    usage_obj = getattr(resp_obj, "usage", None)
                    if usage_obj and actual_conversation_id:
                        bg_usage = cls._extract_usage_from_obj(usage_obj)
                        cls._log_usage(bg_usage, user_id, actual_conversation_id, mode)

                if getattr(bg_event, "type", "") == "response.image_generation_call.partial_image":
                    bg_b64 = getattr(bg_event, "partial_image_b64", "")
                    if bg_b64:
                        try:
                            img_bytes = base64.b64decode(bg_b64)
                            s3_url = storage_service.upload_image_from_bytes(img_bytes, "image/png", folder="flashcard_assets")
                            
                            if stream_manager:
                                stream_manager._send({
                                    "action": "partial_image_stream",
                                    "intent": "flashcards",
                                    "index": 0,
                                    "image_b64": s3_url
                                })
                                
                            final_url = s3_url
                        except Exception as upload_err:
                            logger.warning(f"Background image upload failed: {upload_err}")

            if final_url:
                result_container["image_url"] = final_url
                
                if stream_manager:
                    stream_manager._send({
                        "action": "final_image_stream",
                        "intent": "flashcards",
                        "image_b64": final_url,
                        "revised_prompt": image_prompt
                    })
                    
                if user_id:
                    try:
                        active_session = actual_conversation_id if actual_conversation_id else f"fc_bg_{user_id[-6:]}"
                        image_tracker = ImageUsageService()
                        image_tracker.log_image_usage(
                            user_id=user_id,
                            conversation_id=active_session,
                            source="flashcards",
                            tier=mode,
                            engine=active_config.image_model,
                            size=get_image_generation_size(),
                            quality=active_config.image_quality,
                            partials=get_image_generation_partials(),
                            image_count=1,
                            image_url=final_url
                        )
                    except Exception as tracker_err:
                        logger.error(f"Failed to log background flashcard image usage: {tracker_err}")

        except Exception as e:
            logger.error(f"Background flashcard image generation failed: {e}")

    @staticmethod
    def get_system_instruction(topic: str, num_questions: int) -> Dict[str, Any]:
        """
        Builds the system instruction specifically tailored for flashcards
        using the externalized prompt configuration.
        """
        instruction_text = get_flashcard_system_prompt(topic, num_questions)

        return {
            "role": "system", 
            "content": instruction_text
        }

    @classmethod
    def execute_flashcards_generation(
        cls,
        message: str | None,
        conversation_input: List[Dict[str, Any]],
        user_id: str | None,
        mode: str,
        actual_conversation_id: str | None = None,
        stream_manager: Any | None = None,
        num_questions: int = 0
    ) -> Tuple[str, Dict | None]:
        
        # --- NEW CENTRALIZED BOUNDING LOGIC ---
        if num_questions < 1:
            num_questions = random.randint(7, 13) # 10 plus or minus 3
        elif num_questions > 30:
            num_questions = 30
        # --------------------------------------

        topic_hint = message if message else "General Topic"

        log_event("flashcard_generation_started", {
            "topic": topic_hint,
            "num_questions_requested": num_questions,
            "conversation_id": actual_conversation_id
        })

        system_instruction = cls.get_system_instruction(topic_hint, num_questions)
        conversation_input.append(system_instruction)

        if stream_manager:
            stream_manager.send_status_update(
                category="Preparando flashcards...",
                loading_phrases=["Estructurando conceptos", "Diseñando entorno", "Sintetizando respuestas"]
            )

        image_result = {"image_url": None}
        image_thread = None

        client = get_openai_client()
        active_config = get_model_config(mode)

        final_reply_text = "Aqui tienes tus flashcards listas para estudiar."
        flashcard_data = None

        try:
            req = {
                "model": active_config.model,
                "input": conversation_input,
                "text_format": FlashcardsPayload
            }

            cards_list = []
            parsed_deck = None
            refusal_message = None
            
            has_sent_intent = False

            with client.responses.stream(**req) as stream:
                parser_generator = StreamParser.parse_flashcard_stream(stream)
                
                for event in parser_generator:
                    event_type = event.get("type", "")
                    
                    if event_type == "refusal":
                        refusal_message = event.get("reason", "Refused")
                        break
                        
                    elif event_type == "image_request":
                        # We intercepted the natively generated image prompt. Launch the thread now!
                        prompt_text = event.get("prompt")
                        if prompt_text and stream_manager:
                            image_thread = threading.Thread(
                                target=cls._bg_image_worker,
                                args=(prompt_text, user_id, actual_conversation_id, mode, stream_manager, image_result)
                            )
                            image_thread.start()

                    elif event_type == "card":
                        card_data = event.get("data", {})
                        if isinstance(card_data, dict):
                            if "reasoning" in card_data:
                                del card_data["reasoning"]
                                
                            cards_list.append(card_data)
                            
                            if stream_manager:
                                if not has_sent_intent:
                                    stream_manager.send_intent("flashcards")
                                    has_sent_intent = True
                                    
                                stream_manager.send_flashcard_item(card_data, event.get("index", 0))
                                
                    elif event_type == "done":
                        parsed_deck = event.get("full_response")
                        
                    elif event_type == "usage_metrics" and actual_conversation_id:
                        cls._log_usage(event.get("data"), user_id, actual_conversation_id, mode)

            if refusal_message:
                logger.warning(f"Model refused flashcard generation: {refusal_message}")
                final_reply_text = "Lo siento, no puedo generar flashcards sobre este tema por politicas de seguridad."
                
                if image_thread:
                    image_thread.join()
                    
                return final_reply_text, None

            flashcard_data = {
                "type": "flashcards_data",
                "topic": getattr(parsed_deck, 'topic', 'Flashcards') if parsed_deck else topic_hint,
                "cards": cards_list,
                "count": len(cards_list),
                "background_image": None 
            }

        except Exception as e:
            logger.error(f"Flashcard Generation Error: {e}")
            log_event("flashcard_generation_failed", {"error": str(e)}, level="error")
            final_reply_text = "Error: No pudimos generar las flashcards. Intenta de nuevo."
            flashcard_data = None

        finally:
            if image_thread:
                image_thread.join()
                
            if flashcard_data and image_result.get("image_url"):
                flashcard_data["background_image"] = image_result["image_url"]

        return final_reply_text, flashcard_data