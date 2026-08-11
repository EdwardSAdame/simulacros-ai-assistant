# Backend: simulacros-ai-assistant
# File: src/services/conversation_service.py

import logging
from typing import Dict, Any, Tuple, List, Optional
from decimal import Decimal

from src.utils.logging_utils import log_event
from src.storage.conversations_table import (
    save_conversation, 
    _find_conversation_timestamp, 
    get_conversation_metadata,
    update_conversation_last_active,
    update_conversation_mode,
    update_conversation_exam_context,
    update_conversation_activity,
    get_latest_conversation_for_user 
)
from src.storage.messages_table import save_message
from src.storage.arenas_table import update_arena_last_active

logger = logging.getLogger(__name__)

class ConversationService:
    """
    Encapsulates all database interactions for conversation state management.
    Ensures the Single Responsibility Principle by decoupling DB logic from AI orchestration.
    """

    @staticmethod
    def normalize_email(val: str | None) -> str | None:
        if val is None: return None
        if isinstance(val, str) and val.strip() == "": return None
        return val

    @staticmethod
    def normalize_page(val: str | None) -> str:
        if not val or (isinstance(val, str) and val.strip() == ""):
            return "/"
        return val

    @staticmethod
    def _floats_to_decimals(obj: Any) -> Any:
        """
        Recursively traverses a dictionary or list and converts any float 
        into a decimal.Decimal to comply with AWS Boto3 DynamoDB constraints.
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: ConversationService._floats_to_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ConversationService._floats_to_decimals(v) for v in obj]
        return obj

    @classmethod
    def resolve_and_update_conversation(
        cls,
        user_id: str | None,
        conversation_id: str | None,
        name: str | None,
        email: str | None,
        page: str | None,
        message: str | None,
        mode: str,
        exam_context: str,
        arena_id: str | None = None,
        intent: str = "chat"
    ) -> Tuple[str, str]:
        """
        Checks if a conversation exists. 
        Enforces Sticky Exam Context (Ratchet Logic) so the AI never downgrades to 'general'.
        Manages CurrentActivity state so the router knows if the user is in a Quiz/Flashcard panel.
        Returns a tuple of (actual_conversation_id, final_locked_exam_context).
        """
        page = cls.normalize_page(page)
        sanitized_email = cls.normalize_email(email)

        actual_conversation_id = conversation_id
        should_create_new = True
        
        final_exam_context = str(exam_context).upper()
        persisted_exam_context = None
        persisted_activity = "chat"

        if conversation_id and user_id:
            exists_timestamp = _find_conversation_timestamp(user_id, conversation_id)
            if exists_timestamp:
                should_create_new = False
                existing_meta = get_conversation_metadata(user_id, conversation_id)
                if existing_meta:
                    persisted_exam_context = str(existing_meta.get("ExamContext", "")).upper()
                    persisted_mode = existing_meta.get("AiMode")
                    persisted_activity = existing_meta.get("CurrentActivity", "chat")
                    
                    if persisted_mode and mode != persisted_mode:
                        update_conversation_mode(user_id, conversation_id, mode)
                        log_event("ai_mode_updated_in_db", {"old_mode": persisted_mode, "new_mode": mode})

                    if not arena_id and existing_meta.get("ArenaId"):
                        arena_id = existing_meta.get("ArenaId")

        if should_create_new and user_id and user_id != "anonymous":
            try:
                latest_meta = get_latest_conversation_for_user(user_id)
                if latest_meta:
                    persisted_exam_context = str(latest_meta.get("ExamContext", "")).upper()
                    logger.info(f"Inheriting global exam context {persisted_exam_context} for new conversation.")
            except Exception as e:
                logger.warning(f"Could not retrieve latest user conversation for context inheritance: {e}")

        specific_exams = ["UNAL", "ICFES"]
        if persisted_exam_context in specific_exams and final_exam_context not in specific_exams:
            final_exam_context = persisted_exam_context

        major_intents = ["quiz", "flashcards", "mentalmap", "mind_map", "creative_image", "admission_stats"]
        final_activity = intent if intent in major_intents else (persisted_activity if not should_create_new else "chat")

        try:
            if should_create_new:
                conversation_data = save_conversation(
                    user_id=user_id, 
                    name=name or "", 
                    email=sanitized_email,
                    title=(message or "[Sin texto]")[:40], 
                    page=page,
                    conversation_id=actual_conversation_id,
                    arena_id=arena_id,
                    ai_mode=mode,
                    exam_context=final_exam_context,
                    current_activity=final_activity
                )
                actual_conversation_id = conversation_data["ConversationId"]
            else:
                if persisted_exam_context and final_exam_context != persisted_exam_context:
                    update_conversation_exam_context(user_id, actual_conversation_id, final_exam_context)
                
                if final_activity != persisted_activity:
                    update_conversation_activity(user_id, actual_conversation_id, final_activity)
            
            if user_id and actual_conversation_id:
                update_conversation_last_active(user_id, actual_conversation_id)
                if arena_id:
                     update_arena_last_active(user_id, arena_id)

        except Exception as e:
            logger.error(f"Failed to save/reuse conversation: {e}")
            raise RuntimeError(f"Failed to save/reuse conversation: {e}")

        return actual_conversation_id, final_exam_context

    @classmethod
    def save_hidden_context(cls, conversation_id: str, message: str | None) -> Tuple[str, str, str, None]:
        """Saves a hidden system injection message silently to the database."""
        try:
            save_message(
                conversation_id, 
                role="user", 
                message_text=message if message else "[Hidden Context]",
                metadata={"is_hidden": True, "type": "system_injection"} 
            )
            return "Context saved silently.", conversation_id, "", None
        except Exception as e:
            logger.error(f"Failed to save hidden context: {e}")
            raise RuntimeError(f"Failed to save hidden context: {e}")

    @classmethod
    def save_user_message(cls, conversation_id: str, message: str | None, attachments: List[Dict[str, Any]] | None = None):
        """Saves the user's incoming message and any attached files to the database."""
        try:
            save_message(
                conversation_id, 
                role="user", 
                message_text=message if message else "[Archivo adjunto]", 
                metadata={"attachments": attachments} if attachments else None
            )
        except Exception as e:
            logger.error(f"Failed to save user message: {e}")
            raise RuntimeError(f"Failed to save user message: {e}")

    @classmethod
    def save_assistant_message(cls, conversation_id: str, final_reply_text: str, meta_payload: Dict | None) -> str:
        """Saves the AI's response to the database and returns the generated timestamp."""
        safe_reply_text = final_reply_text.strip() if final_reply_text else "\u200b"

        if safe_reply_text == "\u200b" and not (meta_payload and meta_payload.get("assets")):
             safe_reply_text = "[Generacion completada sin texto]"

        sanitized_meta_payload = cls._floats_to_decimals(meta_payload) if meta_payload else None

        assistant_timestamp = ""
        try:
            saved_item = save_message(
                conversation_id, role="assistant", message_text=safe_reply_text, metadata=sanitized_meta_payload
            )
            if saved_item and isinstance(saved_item, dict):
                assistant_timestamp = saved_item.get("Timestamp", "")
        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}")
            raise RuntimeError(f"Failed to save assistant message: {e}")

        return assistant_timestamp