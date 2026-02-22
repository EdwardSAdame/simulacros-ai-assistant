# src/services/chat_service.py
import re
import logging
import random  # 🟢 IMPORT: Added random for response rotation
from typing import Tuple, Dict, Any, List

# CONFIG
from src.config.settings import get_vector_search_max_results
from src.config.page_vectorstores import get_stores_for_page
from src.config.web_search_config import get_search_filters 
from src.utils.logging_utils import log_event

# SERVICES
from src.services.context_builder import build_runtime_context
from src.services.arena_service import arena_service
from src.services.context_resolution import determine_exam_context
from src.services.history_service import build_history_list

# STORAGE
from src.storage.conversations_table import (
    save_conversation, 
    _find_conversation_timestamp, 
    get_conversation_metadata,
    update_conversation_last_active,
    update_conversation_mode 
)
from src.storage.messages_table import save_message
from src.storage.arenas_table import update_arena_last_active

logger = logging.getLogger(__name__)

def _normalize_email_for_storage(val):
    if val is None: return None
    if isinstance(val, str) and val.strip() == "": return None
    return val

def _normalize_page(val: str | None) -> str:
    if not val or (isinstance(val, str) and val.strip() == ""):
        return "/"
    return val

def get_ai_response(
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
    category: str = "general", # 🟢 SECURITY: Category parameter
    requires_visuals: bool = False,
    stream_manager: Any | None = None,
    arena_id: str | None = None  
) -> Tuple[str, str, str, Dict | None]: 
    
    # Lazy Imports
    from src.assistant.assistant_client import send_message_to_assistant, generate_structured_quiz, stream_structured_quiz
    from src.assistant.image_handler import format_image_urls_for_openai
    from src.services.quiz_service import QuizService
    from src.config.system_instructions import build_system_instructions

    page = _normalize_page(page)

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

    # 2. Intelligence Layer
    exam_context = determine_exam_context(page, message)
    selected_vector_stores = get_stores_for_page(page)
    web_search_config = get_search_filters(exam_context)
    is_web_search_active = (web_search_config is not None)

    log_event("context_resolution", {
        "user_id": user_id,
        "input_url": page,
        "derived_exam": exam_context, 
        "web_search_active": is_web_search_active,
        "trigger_message": message[:50] if message else "None",
        "media_count": len(media_items)
    })

    # 2. Conversation Management
    actual_conversation_id = conversation_id
    should_create_new = True

    if conversation_id and user_id:
        exists_timestamp = _find_conversation_timestamp(user_id, conversation_id)
        if exists_timestamp:
            should_create_new = False
            
            existing_meta = get_conversation_metadata(user_id, conversation_id)
            if existing_meta:
                persisted_mode = existing_meta.get("AiMode")
                if persisted_mode:
                    if mode != persisted_mode:
                        update_conversation_mode(user_id, conversation_id, mode)
                        log_event("ai_mode_updated_in_db", {"old_mode": persisted_mode, "new_mode": mode})
                    else:
                        log_event("ai_mode_verified_with_db", {"mode": mode})

                if not arena_id and existing_meta.get("ArenaId"):
                    arena_id = existing_meta.get("ArenaId")
                    log_event("arena_context_resolved_from_db", {"arena_id": arena_id})
                    
            log_event("conversation_verified_and_reused", {"conversation_id": conversation_id})
        else:
            actual_conversation_id = conversation_id 

    try:
        if should_create_new:
            sanitized_email = _normalize_email_for_storage(email)
            conversation_data = save_conversation(
                user_id=user_id, 
                name=name or "", 
                email=sanitized_email,
                title=(message or "[Sin texto]")[:40], 
                page=page,
                conversation_id=actual_conversation_id,
                arena_id=arena_id,
                ai_mode=mode  
            )
            actual_conversation_id = conversation_data["ConversationId"]
        
        if user_id and actual_conversation_id:
            update_conversation_last_active(user_id, actual_conversation_id)
            if arena_id:
                 update_arena_last_active(user_id, arena_id)

    except Exception as e:
        raise RuntimeError(f"Failed to save/reuse conversation: {e}")

    # 3. Build History & Inputs
    conversation_input = build_history_list(actual_conversation_id)
    
    current_user_content = []
    if message:
        current_user_content.append({"type": "input_text", "text": message})
    
    if clean_images:
        current_user_content.extend(format_image_urls_for_openai(clean_images))

    if current_user_content:
        conversation_input.append({"role": "user", "content": current_user_content})

    # ------------------------------------------------------------------
    # BRANCH: QUIZ vs CHAT
    # ------------------------------------------------------------------
    quiz_data = None
    final_reply_text = ""
    generated_assets = [] 
    sources_data = [] 
    
    if intent == "quiz":
        topic_hint = message if message else "General Knowledge"
        num_questions = 5
        if message:
            match = re.search(r'\b(\d+)\b', message)
            if match:
                parsed_num = int(match.group(1))
                if 1 <= parsed_num <= 10: 
                    num_questions = parsed_num

        conversation_input.append(QuizService.get_system_instruction(topic=topic_hint, num_questions=num_questions))

        try:
            if stream_manager:
                stream_gen = stream_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id,
                    page=page,
                    name=(name or None),
                    email=_normalize_email_for_storage(email),
                    mode=mode, 
                    exam_context=exam_context,
                    requires_visuals=requires_visuals, 
                    pdf_urls=clean_pdfs
                )
                
                seen_indices = set()
                accumulated_questions = []
                final_reply_text = "Aquí tienes tu simulacro."
                ai_generated_title = "Simulacro Generado" 
                
                ghost_easier = None
                ghost_harder = None
                ghost_retry = None

                for event in stream_gen:
                    evt_type = event.get("type")
                    if evt_type == "intro":
                        final_reply_text = event.get("text", "")
                    elif evt_type == "question":
                        q_data = event.get("data")
                        q_dict = q_data.dict()
                        idx = event.get("index", 0)
                        stream_manager.send_quiz_item(question_data=q_dict, index=idx)
                        if idx not in seen_indices:
                            accumulated_questions.append(q_dict)
                            seen_indices.add(idx)
                    elif evt_type == "done":
                        final_obj = event.get("full_response")
                        parsed_response = None
                        if hasattr(final_obj, 'questions'): parsed_response = final_obj
                        elif hasattr(final_obj, 'parsed') and hasattr(final_obj.parsed, 'questions'): parsed_response = final_obj.parsed
                        elif hasattr(final_obj, 'output_parsed') and hasattr(final_obj.output_parsed, 'questions'): parsed_response = final_obj.output_parsed
                        
                        if parsed_response:
                            final_reply_text = parsed_response.intro_message
                            accumulated_questions = [q.dict() for q in parsed_response.questions]
                            if hasattr(parsed_response, 'title') and parsed_response.title:
                                ai_generated_title = parsed_response.title
                            
                            if hasattr(parsed_response, 'easier_payload'): ghost_easier = parsed_response.easier_payload
                            if hasattr(parsed_response, 'harder_payload'): ghost_harder = parsed_response.harder_payload
                            if hasattr(parsed_response, 'retry_payload'): ghost_retry = parsed_response.retry_payload

                    elif evt_type == "error":
                        error_msg = event.get("error", "Unknown stream error")
                        stream_manager.send_error(error_msg)

                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": ai_generated_title,
                    "questions": accumulated_questions,
                    "question_count": len(accumulated_questions),
                    "easier_payload": ghost_easier,
                    "harder_payload": ghost_harder,
                    "retry_payload": ghost_retry
                }

            else:
                # Batch Mode
                quiz_model = generate_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id,
                    page=page,
                    name=(name or None),
                    email=_normalize_email_for_storage(email),
                    mode=mode, 
                    exam_context=exam_context,
                    requires_visuals=requires_visuals, 
                    pdf_urls=clean_pdfs
                )
                
                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": quiz_model.title,
                    "questions": [q.dict() for q in quiz_model.questions],
                    "question_count": len(quiz_model.questions),
                    "easier_payload": getattr(quiz_model, 'easier_payload', None),
                    "harder_payload": getattr(quiz_model, 'harder_payload', None),
                    "retry_payload": getattr(quiz_model, 'retry_payload', None)
                }
                final_reply_text = quiz_model.intro_message

        except Exception as e:
            logger.error(f"Quiz Generation Error: {e}")
            log_event("quiz_generation_failed", {"error": str(e)}, level="error")
            final_reply_text = "**Error**: No pudimos generar el simulacro."
            quiz_data = None

    else:
        # STANDARD CHAT MODE
        try:
            # SECURITY INTERCEPTOR: Bypass OpenAI entirely for identity questions
            if category == "identity_protection":
                logger.info("Intercepted identity question. Returning minimalist Invicto response.")
                
                # The minimalist, slick response pool
                identity_responses = [
                    "Soy Invicto AI.",
                    "Soy una inteligencia artificial desarrollada por Invicto.",
                    "Soy Invicto AI, un sistema exclusivo de Invicto.",
                    "Mi tecnología fue desarrollada internamente por Invicto.",
                    "Soy el asistente de inteligencia artificial de Invicto."
                ]
                
                final_reply_text = random.choice(identity_responses)
                generated_assets = []
                sources_data = []
            
            # NORMAL CHAT ROUTE
            else:
                runtime_signals = build_runtime_context(
                    page=page,
                    user_id=user_id,
                    name=name,
                    email=email,
                    requires_visuals=requires_visuals 
                )

                # Check for Arena FIRST.
                system_prompt = ""
                
                if arena_id:
                    try:
                        logger.info(f"Attempting to fetch context for Arena: {arena_id}")
                        arena_context = arena_service.get_arena_context(user_id, arena_id)
                        
                        if arena_context:
                            arena_title = arena_context.get('Title', 'Custom Arena')
                            arena_instructions = arena_context.get('SystemInstructions', '')
                            
                            arena_vector_store = arena_context.get('VectorStoreId')
                            if arena_vector_store:
                                if not selected_vector_stores:
                                    selected_vector_stores = []
                                selected_vector_stores.append(arena_vector_store)
                                logger.info(f"Attached Arena Vector Store: {arena_vector_store}")

                            if arena_instructions and str(arena_instructions).strip():
                                logger.info(f"Using Exclusive Arena Context: {arena_title}")
                                
                                # 1. Technical Baseline
                                base_tech_prompt = (
                                    "You are an advanced AI Assistant. \n"
                                    "OUTPUT RULES:\n"
                                    "- Use Markdown for formatting.\n"
                                    "- Use LaTeX for math equations (e.g. $E=mc^2$).\n"
                                    "- Be helpful, clear, and accurate.\n"
                                )
                                
                                if runtime_signals:
                                    context_str = "\n".join(runtime_signals)
                                    base_tech_prompt += f"\nCONTEXT:\n{context_str}\n"

                                # Cleaner Injection
                                injection = (
                                    f"\n\n## Identity: {arena_title}\n"
                                    f"{arena_instructions}"
                                )
                                
                                system_prompt = base_tech_prompt + injection
                            else:
                                logger.warning(f"Arena {arena_id} found, but SystemInstructions is empty.")
                        else:
                            logger.warning(f"Arena {arena_id} context not found in DB.")
                                
                    except Exception as e:
                        logger.error(f"Failed to load arena context: {e}")

                # FALLBACK
                if not system_prompt:
                    system_prompt = build_system_instructions(
                        extras=runtime_signals,
                        exam_context=exam_context,
                        requires_visuals=requires_visuals,
                        web_search_active=is_web_search_active 
                    )

                # 3. Call AI
                response_tuple = send_message_to_assistant(
                    conversation_input=conversation_input,
                    user_id=user_id,
                    page=page,
                    name=(name or None),
                    email=_normalize_email_for_storage(email),
                    mode=mode, 
                    system_instruction=system_prompt, 
                    vector_store_ids=selected_vector_stores,
                    requires_visuals=requires_visuals,
                    web_search_config=web_search_config,
                    pdf_urls=clean_pdfs
                )
                
                final_reply_text = response_tuple[0]
                generated_assets = response_tuple[1]
                sources_data = response_tuple[2] if len(response_tuple) > 2 else []

        except Exception as e:
            raise RuntimeError(f"OpenAI Chat API failed: {e}")

    # Step 7: Persist
    assistant_timestamp = ""
    try:
        # Save user message WITH 'sentImages'
        save_message(
            actual_conversation_id, 
            role="user", 
            message_text=message if message else "[Archivo adjunto]",
            metadata={"sentImages": media_items} 
        )
        
        # Save Assistant Response
        meta_payload = quiz_data
        if not meta_payload: meta_payload = {}  
        
        if generated_assets and requires_visuals:
            meta_payload["type"] = "rich_chat"
            meta_payload["assets"] = [{"type": "image", "url": url, "alt": "Generated Visualization"} for url in generated_assets]
        
        if sources_data:
            meta_payload["sources"] = sources_data
        if not meta_payload: meta_payload = None

        saved_item = save_message(
            actual_conversation_id, 
            role="assistant", 
            message_text=final_reply_text,
            metadata=meta_payload
        )
        if saved_item and isinstance(saved_item, dict):
            assistant_timestamp = saved_item.get("Timestamp", "")

    except Exception as e:
        raise RuntimeError(f" Failed to save messages: {e}")

    return final_reply_text, actual_conversation_id, assistant_timestamp, meta_payload