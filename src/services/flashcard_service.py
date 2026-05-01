# src/services/flashcard_service.py
import logging
from typing import Dict, Any, List, Tuple

from src.utils.logging_utils import log_event
from src.config.settings import get_openai_client
from src.config.model_config import get_model_config
from src.services.token_usage_service import TokenUsageService
from src.schemas.flashcard_schemas import FlashcardsPayload
from src.config.flashcard_instructions import get_flashcard_system_prompt

logger = logging.getLogger(__name__)

class FlashcardsService:
    """
    Encapsulates logic for generating study flashcards.
    Utilizes OpenAI's Responses API to guarantee schema adherence.
    """

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
        
        if num_questions < 1:
            num_questions = 5

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
                loading_phrases=["Estructurando conceptos", "Sintetizando respuestas", "Diseñando cartas"]
            )

        client = get_openai_client()
        active_config = get_model_config(mode)

        final_reply_text = "Aquí tienes tus flashcards listas para estudiar."
        flashcard_data = None

        try:
            # 🟢 UPDATED: Requesting the correct Pydantic Schema
            response = client.responses.parse(
                model=active_config.model,
                input=conversation_input,
                text_format=FlashcardsPayload,
            )

            parsed_deck = None
            refusal_message = None

            for output in response.output:
                if getattr(output, "type", "") != "message":
                    continue
                
                for item in getattr(output, "content", []):
                    if getattr(item, "type", "") == "refusal":
                        refusal_message = getattr(item, "refusal", "Refused")
                        continue
                    
                    if hasattr(item, "parsed") and item.parsed:
                        parsed_deck = item.parsed

            if refusal_message:
                logger.warning(f"Model refused flashcard generation: {refusal_message}")
                final_reply_text = "Lo siento, no puedo generar flashcards sobre este tema por políticas de seguridad."
                return final_reply_text, None

            # 🟢 UPDATED: Accessing the 'cards' and 'topic' attributes defined in the schema
            if parsed_deck and hasattr(parsed_deck, 'cards'):
                cards_list = [card.dict() if hasattr(card, 'dict') else card for card in parsed_deck.cards]
                
                flashcard_data = {
                    "type": "flashcards_data",
                    "topic": getattr(parsed_deck, 'topic', 'Flashcards'),
                    "cards": cards_list,
                    "count": len(cards_list)
                }

            if hasattr(response, 'usage') and actual_conversation_id:
                cls._log_usage(response.usage, user_id, actual_conversation_id, mode)

        except Exception as e:
            logger.error(f"Flashcard Generation Error: {e}")
            log_event("flashcard_generation_failed", {"error": str(e)}, level="error")
            final_reply_text = "**Error**: No pudimos generar las flashcards. Intenta de nuevo."
            flashcard_data = None

        return final_reply_text, flashcard_data