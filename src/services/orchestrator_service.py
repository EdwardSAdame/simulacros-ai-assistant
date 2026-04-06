# src/services/orchestrator_service.py
import logging
from typing import Dict, Any, Tuple, List

from src.utils.logging_utils import log_event
from src.assistant.image_handler import format_image_urls_for_openai
from src.services.context_resolution import determine_exam_context

# State Management
from src.services.conversation_service import ConversationService
from src.services.history_service import build_history_list
from src.services.token_usage_service import TokenUsageService # 🟢 NEW: Import the tracking service

# Domain Services
from src.services.chat_service import ChatService
from src.services.quiz_service import QuizService
from src.services.creative_image_service import CreativeImageService
from src.services.admission_chat_service import AdmissionChatService

logger = logging.getLogger(__name__)

class OrchestratorService:
    """
    The central brain of the AI workflow. 
    Routes requests to the appropriate domain service based on intent, 
    and delegates database persistence to the ConversationService.
    """

    @classmethod
    def process_ai_request(
        cls,
        message: str | None,
        user_id: str | None,
        name: str | None,
        email: str | None,
        page: str | None,
        conversation_id: str | None = None,
        image_urls: list[str] | None = None,
        pdf_urls: list[str] | None = None,
        media_items: List[Dict[str, Any]] | None = None,
        mode: str = "omega",
        intent: str = "chat",
        category: str = "general",
        requires_visuals: bool = False,
        stream_manager: Any | None = None,
        arena_id: str | None = None,
        is_hidden: bool = False,
        num_questions: int = 5
    ) -> Tuple[str, str, str, Dict | None]:
        
        # 1. Normalize Media
        if not media_items:
            media_items = []
            if image_urls:
                for url in image_urls:
                    media_items.append({"url": url, "type": "image", "name": "image"})
            if pdf_urls:
                for url in pdf_urls:
                    media_items.append({"url": url, "type": "application/pdf", "name": "document.pdf"})

        clean_images = [m["url"] for m in media_items if "image" in m.get("type", "").lower() or not ".pdf" in m["url"].lower()]
        clean_pdfs   = [m["url"] for m in media_items if "pdf" in m.get("type", "").lower() or ".pdf" in m["url"].lower()]

        # 2. Hidden Context Fast-Path
        if is_hidden:
            return ConversationService.save_hidden_context(conversation_id or "temp", message)

        # 3. Resolve Context and Database State
        raw_exam_context = determine_exam_context(page, message) 

        actual_conversation_id, locked_exam_context = ConversationService.resolve_and_update_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            name=name,
            email=email,
            page=page,
            message=message,
            mode=mode,
            exam_context=raw_exam_context,
            arena_id=arena_id
        )

        # 4. Save User Input
        ConversationService.save_user_message(actual_conversation_id, message, media_items)

        # 5. Build Conversation History
        conversation_input = build_history_list(actual_conversation_id)
        current_user_content = []
        if message:
            current_user_content.append({"type": "input_text", "text": message})
        if clean_images:
            current_user_content.extend(format_image_urls_for_openai(clean_images))
        if current_user_content:
            conversation_input.append({"role": "user", "content": current_user_content})

        # 6. Route to Specific Domain Service
        log_event("orchestrator_routing", {"intent": intent, "category": category, "conversation_id": actual_conversation_id, "locked_exam_context": locked_exam_context})
        
        final_reply_text = ""
        meta_payload = None
        
        try:
            if intent == "quiz":
                final_reply_text, meta_payload = QuizService.execute_quiz_generation(
                    message=message, 
                    conversation_input=conversation_input, 
                    user_id=user_id,
                    name=name, 
                    email=email, 
                    page=page, 
                    mode=mode, 
                    exam_context=locked_exam_context, 
                    stream_manager=stream_manager, 
                    category=category, 
                    clean_pdfs=clean_pdfs,
                    actual_conversation_id=actual_conversation_id
                )
                
            elif intent == "creative_image":
                final_reply_text, final_images_urls, token_usage = CreativeImageService.generate_image(
                    conversation_input=conversation_input, 
                    user_id=user_id, 
                    page=page, 
                    name=name, 
                    email=email, 
                    mode=mode, 
                    stream_manager=stream_manager,
                    conversation_id=actual_conversation_id # 🟢 FIX: Passed the actual ConversationId to the Image Service
                )
                
                # 🟢 NEW: Save the text model's tokens to the TokenUsageTable
                if token_usage:
                    try:
                        TokenUsageService().log_token_usage(
                            user_id=user_id or "anonymous",
                            session_id=actual_conversation_id,
                            model=mode, # This logs it identically to standard text chat!
                            input_tokens=token_usage.get("input_tokens", 0),
                            output_tokens=token_usage.get("output_tokens", 0),
                            total_tokens=token_usage.get("total_tokens", 0)
                        )
                        logger.info(f"Image generation text tokens successfully logged for user {user_id}")
                    except Exception as token_err:
                        logger.error(f"Failed to log text tokens for image generation: {token_err}")

                meta_payload = {
                    "type": "rich_chat",
                    "assets": [{"type": "image", "url": url, "alt": "Generated Visualization"} for url in final_images_urls],
                    "token_usage": token_usage 
                }
                
            elif intent == "admission_stats":
                final_reply_text, meta_payload = AdmissionChatService.execute_admission_chat(
                    conversation_input=conversation_input, user_id=user_id, page=page, 
                    name=name, email=email, mode=mode, exam_context=locked_exam_context, 
                    category=category, actual_conversation_id=actual_conversation_id
                )
                
            else:
                final_reply_text, meta_payload = ChatService.execute_standard_chat(
                    conversation_input=conversation_input, user_id=user_id, page=page, 
                    name=name, email=email, message=message, mode=mode, exam_context=locked_exam_context, 
                    category=category, requires_visuals=requires_visuals, arena_id=arena_id, 
                    clean_pdfs=clean_pdfs, actual_conversation_id=actual_conversation_id
                )
                
        except Exception as e:
            logger.error(f"Domain Service Execution Failed: {e}")
            final_reply_text = "**Error**: Ha ocurrido un error interno de sistema. Intenta de nuevo."
            log_event("orchestrator_failure", {"error": str(e)}, level="error")

        # 7. Persist AI Response
        assistant_timestamp = ConversationService.save_assistant_message(
            actual_conversation_id, final_reply_text, meta_payload
        )

        return final_reply_text, actual_conversation_id, assistant_timestamp, meta_payload