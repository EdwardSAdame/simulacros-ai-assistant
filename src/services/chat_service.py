# src/services/chat_service.py
import logging
import random
import base64 
import threading 
import math 
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
from src.services.storage_service import storage_service 

# STORAGE
from src.storage.conversations_table import (
    save_conversation, 
    _find_conversation_timestamp, 
    get_conversation_metadata,
    update_conversation_last_active,
    update_conversation_mode,
    update_conversation_exam_context
)
from src.storage.messages_table import save_message
from src.storage.arenas_table import update_arena_last_active

logger = logging.getLogger(__name__)

# --- TESTING TOGGLE ---
QUIZ_FEATURE_ENABLED = True

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
    category: str = "general",
    requires_visuals: bool = False,
    stream_manager: Any | None = None,
    arena_id: str | None = None,
    is_hidden: bool = False,
    num_questions: int = 5
) -> Tuple[str, str, str, Dict | None]: 
    
    from src.assistant.assistant_client import send_message_to_assistant, generate_structured_quiz, stream_structured_quiz, stream_chat_response
    from src.assistant.image_handler import format_image_urls_for_openai
    from src.services.quiz_service import QuizService
    from src.config.system_instructions import build_system_instructions
    from src.services.creative_image_service import CreativeImageService
    from src.services.token_usage_service import TokenUsageService

    def _log_usage(usage_data: dict, current_user: str, session: str, active_mode: str):
        if not usage_data or not current_user: return
        try:
            input_val = usage_data.get("input_tokens", usage_data.get("prompt_tokens", 0))
            output_val = usage_data.get("output_tokens", usage_data.get("completion_tokens", 0))

            TokenUsageService().log_token_usage(
                user_id=current_user,
                session_id=session,
                model=active_mode,
                input_tokens=input_val,
                output_tokens=output_val,
                total_tokens=usage_data.get("total_tokens", 0),
                reasoning_tokens=usage_data.get("reasoning_tokens", 0),
                cached_tokens=usage_data.get("cached_tokens", 0)
            )
        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")

    page = _normalize_page(page)

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

    actual_conversation_id = conversation_id
    should_create_new = True
    persisted_exam_context = None

    if conversation_id and user_id:
        exists_timestamp = _find_conversation_timestamp(user_id, conversation_id)
        if exists_timestamp:
            should_create_new = False
            existing_meta = get_conversation_metadata(user_id, conversation_id)
            if existing_meta:
                persisted_exam_context = existing_meta.get("ExamContext")
                persisted_mode = existing_meta.get("AiMode")
                if persisted_mode:
                    if mode != persisted_mode:
                        update_conversation_mode(user_id, conversation_id, mode)
                        log_event("ai_mode_updated_in_db", {"old_mode": persisted_mode, "new_mode": mode})

                if not arena_id and existing_meta.get("ArenaId"):
                    arena_id = existing_meta.get("ArenaId")
        else:
            actual_conversation_id = conversation_id 

    exam_context = determine_exam_context(page, message, current_locked_context=persisted_exam_context)

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
                ai_mode=mode,
                exam_context=exam_context
            )
            actual_conversation_id = conversation_data["ConversationId"]
        else:
            if persisted_exam_context and exam_context != persisted_exam_context:
                update_conversation_exam_context(user_id, actual_conversation_id, exam_context)
        
        if user_id and actual_conversation_id:
            update_conversation_last_active(user_id, actual_conversation_id)
            if arena_id:
                 update_arena_last_active(user_id, arena_id)

    except Exception as e:
        raise RuntimeError(f"Failed to save/reuse conversation: {e}")

    if is_hidden:
        try:
            save_message(
                actual_conversation_id, 
                role="user", 
                message_text=message if message else "[Hidden Context]",
                metadata={"is_hidden": True, "type": "system_injection"} 
            )
            return "Context saved silently.", actual_conversation_id, "", None
        except Exception as e:
            raise RuntimeError(f"Failed to save hidden context: {e}")

    selected_vector_stores = get_stores_for_page(page)
    web_search_config = None if intent == "admission_stats" else get_search_filters(exam_context)
    is_web_search_active = (web_search_config is not None)

    conversation_input = build_history_list(actual_conversation_id)
    
    current_user_content = []
    if message:
        current_user_content.append({"type": "input_text", "text": message})
    if clean_images:
        current_user_content.extend(format_image_urls_for_openai(clean_images))
    if current_user_content:
        conversation_input.append({"role": "user", "content": current_user_content})

    quiz_data = None
    final_reply_text = ""
    generated_assets = [] 
    sources_data = [] 
    
    if intent == "quiz" and QUIZ_FEATURE_ENABLED:
        topic_hint = category if category else "General Knowledge"
        
        if not isinstance(num_questions, int) or num_questions < 1:
            num_questions = 5
        elif num_questions > 30:
            num_questions = 30

        creative_categories = ["sociales", "lectura_critica", "ingles", "ciencias_sociales"]
        requires_creative_images = category in creative_categories

        conversation_input.append(QuizService.get_system_instruction(topic=topic_hint, num_questions=num_questions))

        try:
            if stream_manager:
                stream_gen = stream_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id, page=page, name=(name or None), email=_normalize_email_for_storage(email),
                    mode=mode, exam_context=exam_context, requires_visuals=requires_visuals, 
                    requires_creative_images=requires_creative_images, pdf_urls=clean_pdfs,
                    vector_store_ids=selected_vector_stores, web_search_config=web_search_config      
                )
                
                seen_indices = set()
                accumulated_questions = []
                final_reply_text = "Aqui tienes tu simulacro."
                ai_generated_title = "Simulacro Generado" 
                
                ghost_easier = None
                ghost_harder = None
                ghost_retry = None

                image_threads = []
                image_urls_map = {}
                
                max_allowed_visuals = math.floor(num_questions * 0.4) if requires_creative_images else 2
                visuals_triggered_count = 0
                allowed_visual_indices = set() 

                def _bg_image_generator(img_prompt: str, q_index: int):
                    try:
                        from src.config.settings import get_openai_client
                        from src.config.model_config import get_model_config 
                        
                        bg_client = get_openai_client()
                        active_config = get_model_config(mode) 
                        
                        bg_req = {
                            "model": active_config.model, 
                            "input": [{"role": "user", "content": f"Generate this image: {img_prompt}"}],
                            "tools": [{"type": "image_generation", "model": active_config.image_model, "partial_images": 3}],
                            "stream": True
                        }
                        
                        bg_stream = bg_client.responses.create(**bg_req)
                        final_url = None
                        
                        for bg_event in bg_stream:
                            if getattr(bg_event, "type", "") == "response.image_generation_call.partial_image":
                                bg_b64 = getattr(bg_event, "partial_image_b64", "")
                                if bg_b64:
                                    try:
                                        img_bytes = base64.b64decode(bg_b64)
                                        s3_url = storage_service.upload_image_from_bytes(img_bytes, "image/png", folder="quiz_assets")
                                        stream_manager.send_partial_image(index=q_index, b64_data=s3_url)
                                        final_url = s3_url
                                    except Exception as upload_err:
                                        logger.warning(f"BG image upload failed: {upload_err}")
                        
                        if final_url: image_urls_map[q_index] = final_url
                    except Exception as e:
                        logger.error(f"BG image generation failed: {e}")

                # ------------------------------------------------------------------
                # A PRUEBA DE FALLOS: Extracción de File ID con plt.show()
                # ------------------------------------------------------------------
                def _bg_plot_generator(plot_prompt: str, q_index: int):
                    try:
                        from src.config.settings import get_openai_client
                        from src.config.model_config import get_model_config
                        
                        bg_client = get_openai_client()
                        active_config = get_model_config(mode) 
                        
                        # INSTRUCCIÓN CRÍTICA: Obligamos a la IA a usar plt.show()
                        instructions = (
                            "You are a Data Scientist. Write and run python code to generate the requested plot. "
                            "You MUST use plt.show() to display the plot directly so it is attached as an image file. "
                            "Do NOT save it locally."
                        )
                        
                        bg_req = {
                            "model": active_config.model,
                            "input": [{"role": "user", "content": f"Generate a plot for this request: {plot_prompt}"}],
                            "tools": [{"type": "code_interpreter"}], 
                            "instructions": instructions
                        }
                        
                        logger.info(f"Starting Code Interpreter for plot on question {q_index}")
                        response = bg_client.responses.create(**bg_req)
                        
                        file_id = None
                        
                        # BÚSQUEDA EXHAUSTIVA DEL FILE ID
                        for output in getattr(response, "output", []):
                            if getattr(output, "type", "") == "message":
                                for item in getattr(output, "content", []):
                                    
                                    # 1. Buscamos si usó plt.show() (debería venir como image_file)
                                    if getattr(item, "type", "") == "image_file":
                                        img_obj = getattr(item, "image_file", None)
                                        if img_obj: 
                                            file_id = getattr(img_obj, "file_id", file_id)
                                            
                                    # 2. Por si acaso, buscamos si ignoró la orden y lo guardó, dejando una anotación
                                    annotations = getattr(item, "annotations", [])
                                    for ann in annotations:
                                        if getattr(ann, "type", "") in ["container_file_citation", "file_path"]:
                                            file_id = getattr(ann, "file_id", file_id)
                        
                        # SI ENCONTRAMOS LA IMAGEN, LA DESCARGAMOS Y LA ENVIAMOS A WIX
                        if file_id:
                            img_bytes = None
                            try:
                                # Standard OpenAI Files API
                                img_response = bg_client.files.content(file_id)
                                img_bytes = img_response.read()
                            except Exception:
                                # Fallback genérico
                                res = bg_client._get(f"/files/{file_id}/content")
                                img_bytes = res.content
                                    
                            if img_bytes:
                                s3_url = storage_service.upload_image_from_bytes(
                                    img_bytes, "image/png", folder="quiz_assets"
                                )
                                stream_manager.send_partial_image(index=q_index, b64_data=s3_url)
                                image_urls_map[q_index] = s3_url
                                logger.info(f"Plot successfully extracted and uploaded for question {q_index}")
                            else:
                                logger.warning(f"Failed to read bytes for file_id {file_id}")
                        else:
                            logger.warning(f"Code interpreter ran but no file_id was found in output for question {q_index}")
                            
                    except Exception as e:
                        logger.error(f"BG plot generation failed: {e}")

                # ------------------------------------------------------------------

                for event in stream_gen:
                    evt_type = event.get("type")
                    if evt_type == "intro":
                        final_reply_text = event.get("text", "")
                    
                    elif evt_type == "image_request":
                        q_idx = event.get("index", 0)
                        if visuals_triggered_count < max_allowed_visuals:
                            prompt_str = event.get("prompt", "")
                            t = threading.Thread(target=_bg_image_generator, args=(prompt_str, q_idx))
                            t.start()
                            image_threads.append(t)
                            visuals_triggered_count += 1
                            allowed_visual_indices.add(q_idx)

                    elif evt_type == "plot_request":
                        q_idx = event.get("index", 0)
                        if visuals_triggered_count < max_allowed_visuals:
                            prompt_str = event.get("prompt", "")
                            logger.info(f"Triggering async plot generation for question {q_idx}")
                            t = threading.Thread(target=_bg_plot_generator, args=(prompt_str, q_idx))
                            t.start()
                            image_threads.append(t)
                            visuals_triggered_count += 1
                            allowed_visual_indices.add(q_idx)

                    elif evt_type == "question":
                        q_data = event.get("data")
                        q_dict = q_data.dict()
                        idx = event.get("index", 0)
                        
                        if idx not in allowed_visual_indices:
                            q_dict["image_prompt"] = None
                            q_dict["plot_prompt"] = None
                            q_dict["image_url"] = None

                        stream_manager.send_quiz_item(question_data=q_dict, index=idx)
                        
                        if idx not in seen_indices:
                            accumulated_questions.append(q_dict)
                            seen_indices.add(idx)
                            
                    elif evt_type == "partial_image":
                        b64_data = event.get("b64_data", "")
                        if b64_data:
                            try:
                                image_bytes = base64.b64decode(b64_data)
                                s3_url = storage_service.upload_image_from_bytes(
                                    image_bytes, "image/png", folder="quiz_assets"
                                )
                                stream_manager.send_partial_image(index=event.get("index", 0), b64_data=s3_url)
                            except Exception as upload_err:
                                logger.warning(f"Partial image S3 upload failed during quiz: {upload_err}")
                                
                    elif evt_type == "usage_metrics":
                        _log_usage(event.get("data"), user_id, actual_conversation_id, mode)
                        
                    elif evt_type == "done":
                        final_obj = event.get("full_response")
                        parsed_response = None
                        if hasattr(final_obj, 'questions'): parsed_response = final_obj
                        elif hasattr(final_obj, 'parsed') and hasattr(final_obj.parsed, 'questions'): parsed_response = final_obj.parsed
                        elif hasattr(final_obj, 'output_parsed') and hasattr(final_obj.output_parsed, 'questions'): parsed_response = final_obj.output_parsed
                        
                        if parsed_response:
                            final_reply_text = parsed_response.intro_message
                            accumulated_questions = [q.dict() for q in parsed_response.questions]
                            
                            for i, q_dict in enumerate(accumulated_questions):
                                if i not in allowed_visual_indices:
                                    q_dict["image_prompt"] = None
                                    q_dict["plot_prompt"] = None
                                    q_dict["image_url"] = None
                            
                            if hasattr(parsed_response, 'title') and parsed_response.title:
                                ai_generated_title = parsed_response.title
                            
                            if hasattr(parsed_response, 'easier_payload'): ghost_easier = parsed_response.easier_payload
                            if hasattr(parsed_response, 'harder_payload'): ghost_harder = parsed_response.harder_payload
                            if hasattr(parsed_response, 'retry_payload'): ghost_retry = parsed_response.retry_payload

                    elif evt_type == "error":
                        error_msg = event.get("error", "Unknown stream error")
                        stream_manager.send_error(error_msg)

                for t in image_threads:
                    t.join()
                    
                for i, q in enumerate(accumulated_questions):
                    if i in image_urls_map:
                        q["image_url"] = image_urls_map[i]

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
                quiz_model, usage_data = generate_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id, page=page, name=(name or None), email=_normalize_email_for_storage(email),
                    mode=mode, exam_context=exam_context, requires_visuals=requires_visuals, 
                    requires_creative_images=requires_creative_images, pdf_urls=clean_pdfs,
                    vector_store_ids=selected_vector_stores, web_search_config=web_search_config
                )
                
                _log_usage(usage_data, user_id, actual_conversation_id, mode)

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

    elif intent == "creative_image":
        logger.info(f"Routing to Creative Image Service for user {user_id}")
        try:
            final_reply_text, final_images_urls = CreativeImageService.generate_image(
                conversation_input=conversation_input, user_id=user_id, page=page, name=name, email=email, mode=mode, stream_manager=stream_manager
            )
            generated_assets = final_images_urls
            requires_visuals = True 
            quiz_data = None
        except Exception as e:
            logger.error(f"Creative Image Generation Error: {e}")
            final_reply_text = "**Error**: We could not generate the image."
            quiz_data = None

    elif intent == "admission_stats":
        logger.info(f"Routing to Admission Stats local tool for user {user_id}")
        try:
            stream_gen = stream_chat_response(
                conversation_input=conversation_input, user_id=user_id, page=page, name=name, email=email, mode=mode, enable_image_generation=False
            )
            for event in stream_gen:
                if isinstance(event, dict) and event.get("type") == "usage_metrics":
                    _log_usage(event.get("data"), user_id, actual_conversation_id, mode)
                elif getattr(event, "type", "") == "response.output_text.delta":
                    final_reply_text += getattr(event, "delta", "")
                    
            quiz_data = None
            generated_assets = []
            sources_data = []
            
        except Exception as e:
            logger.error(f"Admission Stats Generaton Error: {e}")
            final_reply_text = "**Error**: Hubo un problema consultando la base de datos de admisiones."
            quiz_data = None

    else:
        try:
            if category == "identity_protection":
                logger.info("Intercepted identity question. Returning minimalist Invicto response.")
                identity_responses = [
                    "Soy Invicto AI.",
                    "Soy una inteligencia artificial desarrollada por Invicto.",
                    "Soy Invicto AI, un sistema exclusivo de Invicto.",
                    "Mi tecnologia fue desarrollada internamente por Invicto.",
                    "Soy el asistente de inteligencia artificial de Invicto."
                ]
                final_reply_text = random.choice(identity_responses)
                generated_assets = []
                sources_data = []
            else:
                runtime_signals = build_runtime_context(
                    page=page, user_id=user_id, name=name, email=email, requires_visuals=requires_visuals 
                )

                system_prompt = ""
                if arena_id:
                    try:
                        arena_context = arena_service.get_arena_context(user_id, arena_id)
                        if arena_context:
                            arena_title = arena_context.get('Title', 'Custom Arena')
                            arena_instructions = arena_context.get('SystemInstructions', '')
                            
                            arena_vector_store = arena_context.get('VectorStoreId')
                            if arena_vector_store:
                                if not selected_vector_stores:
                                    selected_vector_stores = []
                                selected_vector_stores.append(arena_vector_store)

                            if arena_instructions and str(arena_instructions).strip():
                                base_tech_prompt = (
                                    "You are an advanced AI Assistant. \n"
                                    "OUTPUT RULES:\n"
                                    "- Use Markdown for formatting.\n"
                                    "- Use LaTeX for math equations.\n"
                                    "- Be helpful, clear, and accurate.\n"
                                )
                                if runtime_signals:
                                    context_str = "\n".join(runtime_signals)
                                    base_tech_prompt += f"\nCONTEXT:\n{context_str}\n"

                                injection = (
                                    f"\n\n## Identity: {arena_title}\n"
                                    f"{arena_instructions}"
                                )
                                system_prompt = base_tech_prompt + injection
                    except Exception as e:
                        logger.error(f"Failed to load arena context: {e}")

                if not system_prompt:
                    system_prompt = build_system_instructions(
                        extras=runtime_signals, exam_context=exam_context, requires_visuals=requires_visuals, web_search_active=is_web_search_active 
                    )

                response_tuple = send_message_to_assistant(
                    conversation_input=conversation_input, user_id=user_id, page=page, name=(name or None), email=_normalize_email_for_storage(email),
                    mode=mode, system_instruction=system_prompt, vector_store_ids=selected_vector_stores, requires_visuals=requires_visuals,
                    web_search_config=web_search_config, pdf_urls=clean_pdfs
                )
                
                final_reply_text = response_tuple[0]
                generated_assets = response_tuple[1]
                sources_data = response_tuple[2] if len(response_tuple) > 2 else []
                
                usage_data = response_tuple[3] if len(response_tuple) > 3 else {}
                _log_usage(usage_data, user_id, actual_conversation_id, mode)

        except Exception as e:
            raise RuntimeError(f"OpenAI Chat API failed: {e}")

    assistant_timestamp = ""
    try:
        save_message(
            actual_conversation_id, role="user", message_text=message if message else "[Archivo adjunto]", metadata={"sentImages": media_items} 
        )
        
        meta_payload = quiz_data
        if not meta_payload: meta_payload = {}  
        
        if generated_assets and requires_visuals:
            meta_payload["type"] = "rich_chat"
            meta_payload["assets"] = [{"type": "image", "url": url, "alt": "Generated Visualization"} for url in generated_assets]
        
        if sources_data:
            meta_payload["sources"] = sources_data
        if not meta_payload: meta_payload = None

        safe_reply_text = final_reply_text.strip() if final_reply_text else "\u200b"

        if safe_reply_text == "\u200b" and not generated_assets:
             safe_reply_text = "[Generación completada sin texto]"

        saved_item = save_message(
            actual_conversation_id, role="assistant", message_text=safe_reply_text, metadata=meta_payload
        )
        if saved_item and isinstance(saved_item, dict):
            assistant_timestamp = saved_item.get("Timestamp", "")

    except Exception as e:
        raise RuntimeError(f" Failed to save messages: {e}")

    return safe_reply_text, actual_conversation_id, assistant_timestamp, meta_payload