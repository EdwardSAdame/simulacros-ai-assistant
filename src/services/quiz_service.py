# src/services/quiz_service.py
from typing import Dict, Any, List, Tuple
import math
import random
import re
import base64
import threading
import queue
import logging

from src.utils.logging_utils import log_event
from src.services.storage_service import storage_service
from src.assistant.assistant_client import generate_structured_quiz, stream_structured_quiz
from src.config.page_vectorstores import get_stores_for_page
from src.config.web_search_config import get_search_filters
from src.services.token_usage_service import TokenUsageService
from src.services.container_usage_service import ContainerUsageService

logger = logging.getLogger(__name__)

def _normalize_email_for_storage(val):
    if val is None: return None
    if isinstance(val, str) and val.strip() == "": return None
    return val

class QuizService:
    """
    Encapsulates logic for Quiz Prompts and Orchestrates Quiz Execution. 
    Parsing is handled by the Assistant Client via Structured Outputs.
    """

    @staticmethod
    def _log_usage(usage_data: dict, current_user: str | None, session: str, active_mode: str):
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
            logger.error(f"Failed to log token usage in quiz service: {e}")

    @staticmethod
    def get_system_instruction(
        topic: str = "general", 
        num_questions: int = 5,
        target_indices: List[int] = None,
        is_general_subject: bool = False,
        is_visual_subject: bool = False,
        is_creative_subject: bool = False
    ) -> Dict[str, Any]:
        """
        Returns the system instruction with optimized token usage and strict, 
        deterministic visual index assignments.
        """
        target_indices = target_indices or []
        target_visuals = len(target_indices)
        null_count = num_questions - target_visuals

        # LLMs understand 1-indexed question numbers much better than 0-indexed arrays
        human_indices = [i + 1 for i in target_indices]
        human_indices_str = ", ".join([f"#{i}" for i in human_indices])

        visual_instruction = ""

        if is_general_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (HYBRID MULTI-SUBJECT - MANDATORY)\n"
                f"You MUST generate EXACTLY {target_visuals} visual(s) across this quiz.\n"
                f"DETERMINISTIC ENFORCEMENT: You MUST generate a visual (`plot_prompt` or `image_prompt`) ONLY for the following specific question numbers: {human_indices_str}.\n"
                f"For the remaining {null_count} questions, BOTH fields MUST be set to a literal JSON null. Do not violate this assignment.\n"
                "CRITICAL VISUAL DEPENDENCY: For questions with a visual, the visual MUST contain the critical data. Do not repeat the data in the text.\n"
                "Analyze the question and select exactly ONE visual engine per visual question:\n"
                "  - **DATA**: For charts, graphs, or geometry -> Write a description in `plot_prompt`. Keep `image_prompt` null.\n"
                "  - **CREATIVE**: For thematic illustrations -> Write a description in `image_prompt`. Keep `plot_prompt` null.\n"
                "CRITICAL: Rely entirely on the background system to execute the chosen visual engine.\n\n"
            )
        elif is_visual_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (DATA GRAPHS - MANDATORY)\n"
                f"You MUST generate EXACTLY {target_visuals} graph(s) for this quiz.\n"
                f"DETERMINISTIC ENFORCEMENT: You MUST write a mathematical description in `plot_prompt` ONLY for the following specific question numbers: {human_indices_str}.\n"
                f"For the remaining {null_count} questions, `plot_prompt` MUST be set to a literal JSON null. Do not write 'none' or empty strings.\n"
                "CRITICAL VISUAL DEPENDENCY: If a question has a graph, the text MUST refer to it (e.g., 'Segun la grafica...') and the student MUST need to look at the graph to find the data. Do NOT give them the numbers in the text.\n"
                "CRITICAL: The background system handles all Python code, Matplotlib styling, colors, and layouts automatically.\n"
                "  - **NATURAL LANGUAGE ONLY**: Write the `plot_prompt` strictly as a plain English/Spanish mathematical description.\n"
                "  - **MATH FOCUSED**: Restrict the `plot_prompt` entirely to mathematical parameters, functions, domains, points, and axis labels. Focus your intelligence on making the math complex and interesting.\n"
                "  - **FIELD ROUTING**: Keep `image_prompt` always null.\n\n"
            )
        elif is_creative_subject and target_visuals > 0:
            visual_instruction = (
                f"## VISUAL GENERATION PROTOCOL (CREATIVE ILLUSTRATIONS - MANDATORY)\n"
                f"You MUST include EXACTLY {target_visuals} contextual illustration(s) in this quiz.\n"
                f"DETERMINISTIC ENFORCEMENT: You MUST write a visual description in `image_prompt` ONLY for the following specific question numbers: {human_indices_str}.\n"
                f"For the remaining {null_count} questions, `image_prompt` MUST be set to a literal JSON null. Do not write 'none' or empty strings.\n"
                "CRITICAL DECORATIVE RULE: The image MUST be purely decorative and metaphorical. It MUST NOT contain any text, sentences, or data required to solve the question. The student should be able to answer the question solely by reading the `context_text` or `question_text`.\n"
                "CRITICAL: Delegate image creation to the background renderer by describing the image exclusively in the `image_prompt` field.\n"
                "  - **FIELD ROUTING**: Keep `plot_prompt` always null.\n\n"
            )
        else:
            visual_instruction = (
                "## VISUAL & TOOL EXECUTION PROTOCOL (TEXT ONLY)\n"
                "Produce a strictly text-based quiz. Keep `image_url`, `image_prompt`, and `plot_prompt` strictly as literal JSON null.\n\n"
            )

        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION\n"
            f"The user requested a quiz/exam about '{topic}'. "
            f"Generate exactly {num_questions} distinct questions.\n\n"
            f"{visual_instruction}"
            "## CRITICAL CONSTRAINTS\n"
            "1. **ORDER OF OPERATIONS**: FIRST, design visuals (`plot_prompt` / `image_prompt`). SECOND, write the `context_text` if a reading passage is required. THIRD, write the `explanation` based on those anchors. FOURTH, write the `question_text` and `options`.\n"
            "2. **DISTINCT EXPLANATION**: Write the `explanation` focusing strictly on the Setup, Solution, and Traps.\n"
            "3. **EXPLICIT ARITHMETIC**: Do NOT use mental math. In your `explanation`, you MUST write out every single arithmetic operation explicitly line-by-line.\n"
            "4. **PREMISE MATCHING**: The mathematical variables, numbers, and scenarios in `question_text` MUST logically match your Setup.\n"
            "5. **ANTI-LEAK DOCTRINE**: `question_text`, `options`, and `feedback` are strictly student-facing. NEVER leak internal meta-labels (e.g., 'Core Constraints', 'The Setup', 'Failure Paths', 'Traps') into these fields.\n\n"
            "## DISTRACTOR GENERATION PROTOCOL\n"
            "- Identify 3 distinct 'Failure Paths' in the `explanation`.\n"
            "- The wrong `options` MUST be the logical result of these specific Failure Paths.\n"
            "- In `feedback`, explicitly explain why the student might have chosen that wrong option without using the word 'Failure Path'.\n\n"
            "## CONTENT & PEDAGOGY RULES\n"
            "- Generate questions strictly applying the 'ACADEMIC FRAMEWORK'.\n"
            "- Assign a `difficulty` integer (1-3) based on cognitive load.\n"
            "- Questions must be challenging, non-trivial, and require multi-step reasoning.\n\n"
            "## SCHEMA & FIELD RESTRICTIONS\n"
            "- **SOURCES**: Keep `source_url` as null unless you actively hold a verified URL in your context for this specific question.\n"
            "- **CONTEXT**: Use `context_text` ONLY if the question requires a large foundational text, reading passage, or shared scenario. Otherwise, keep it null.\n\n"
            "## SMART FOLLOW-UP PROTOCOL\n"
            "Generate 3 'Ghost Prompts' (easier_payload, harder_payload, retry_payload) in the EXACT SAME LANGUAGE as the quiz, using First Person format.\n"
        )

        return {
            "role": "system", 
            "content": [{"type": "input_text", "text": instruction_text}]
        }

    @classmethod
    def execute_quiz_generation(
        cls,
        message: str | None,
        conversation_input: List[Dict[str, Any]],
        user_id: str | None,
        name: str | None,
        email: str | None,
        page: str | None,
        mode: str,
        exam_context: str,
        stream_manager: Any | None = None,
        category: str = "general",
        clean_pdfs: List[str] | None = None,
        actual_conversation_id: str | None = None
    ) -> Tuple[str, Dict | None]:
        
        topic_hint = category if category else "General Knowledge"
        num_questions = 5
        
        if message:
            match = re.search(r'\b(\d+)\b', message)
            if match:
                parsed_num = int(match.group(1))
                if 1 <= parsed_num <= 30: 
                    num_questions = parsed_num

        visual_subjects_list = [
            "matematicas", "matematica", "matemática", "fisica", "física", 
            "quimica", "química", "biologia", "biología", 
            "ciencias_naturales", "analisis_imagen"
        ]
        creative_categories = [
            "ciencias_sociales", "sociales_ciudadanas", "sociales", 
            "lectura_critica", "analisis_textual", "ingles"
        ]

        topic_lower = topic_hint.lower()
        is_general_subject = "general" in topic_lower
        is_visual_subject = any(subj in topic_lower for subj in visual_subjects_list)
        is_creative_subject = any(subj in topic_lower for subj in creative_categories)
        requires_creative_images = is_creative_subject or is_general_subject

        max_visuals = 0
        target_visuals = 0
        target_indices = []

        if is_general_subject or is_visual_subject or is_creative_subject:
            max_visuals = math.floor(num_questions * 0.4)
            target_visuals = random.randint(0, max_visuals) if max_visuals > 0 else 0
            if target_visuals > 0:
                target_indices = sorted(random.sample(range(num_questions), target_visuals))

        log_event("dynamic_visual_quota_calculated", {
            "subject_topic": topic_lower,
            "is_general_subject": is_general_subject,
            "is_visual_subject": is_visual_subject,
            "is_creative_subject": is_creative_subject,
            "num_questions_requested": num_questions,
            "max_allowed_visuals": max_visuals, 
            "target_visuals_enforced": target_visuals,
            "target_indices_assigned": target_indices
        })

        # Fetch Active Container to prevent duplicate billing
        active_container_id = None
        if actual_conversation_id:
            try:
                active_container_id = ContainerUsageService().get_active_container_for_session(actual_conversation_id)
                if active_container_id:
                    logger.info(f"Quiz execution reusing existing container: {active_container_id}")
            except Exception as e:
                logger.error(f"Failed to fetch active container for quiz: {e}")

        system_instruction = cls.get_system_instruction(
            topic=topic_hint, 
            num_questions=num_questions, 
            target_indices=target_indices,
            is_general_subject=is_general_subject,
            is_visual_subject=is_visual_subject,
            is_creative_subject=is_creative_subject
        )
        conversation_input.append(system_instruction)

        selected_vector_stores = get_stores_for_page(page)
        web_search_config = get_search_filters(exam_context)

        quiz_data = None
        final_reply_text = "Aqui tienes tu simulacro."

        try:
            if stream_manager:
                stream_gen = stream_structured_quiz(
                    conversation_input=conversation_input,
                    user_id=user_id, page=page, name=(name or None), email=_normalize_email_for_storage(email),
                    mode=mode, exam_context=exam_context, requires_visuals=False, 
                    requires_creative_images=requires_creative_images, pdf_urls=clean_pdfs,
                    vector_store_ids=selected_vector_stores, web_search_config=web_search_config,
                    category=category
                )
                
                seen_indices = set()
                accumulated_questions = []
                ai_generated_title = "Simulacro Generado" 
                
                ghost_easier, ghost_harder, ghost_retry = None, None, None
                image_threads = []
                plot_queue = queue.Queue()
                image_urls_map = {}
                allowed_visual_indices = set(target_indices)

                def _bg_image_generator(img_prompt: str, q_index: int):
                    try:
                        from src.config.settings import get_openai_client
                        from src.config.model_config import get_model_config 
                        from src.config.creative_image_instructions import get_creative_image_system_prompt
                        
                        bg_client = get_openai_client()
                        active_config = get_model_config(mode) 
                        
                        base_instruction = "You are an expert AI illustrator for Invicto. Use the image_generation tool to create the requested image.\n\n"
                        instructions = base_instruction + get_creative_image_system_prompt()
                        
                        bg_req = {
                            "model": active_config.model, 
                            "input": [{"role": "user", "content": f"Generate this image: {img_prompt}"}],
                            "tools": [{"type": "image_generation", "model": active_config.image_model, "partial_images": 3}],
                            "instructions": instructions,
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

                def _plot_worker():
                    from src.config.settings import get_openai_client, get_code_interpreter_memory
                    from src.config.model_config import get_model_config
                    from src.services.ai_assets_service import AiAssetsService
                    from src.config.visual_instructions import build_visual_instructions
                    
                    bg_client = get_openai_client()
                    active_config = get_model_config(mode)
                    memory_limit = get_code_interpreter_memory()
                    
                    base_instruction = (
                        "Write and run Python code to generate the requested plot.\n"
                        "You MUST use Matplotlib. Save the figure as a .png file in your container environment (e.g., /mnt/data/plot.png). Do NOT use plt.show().\n\n"
                    )
                    instructions = base_instruction + build_visual_instructions()

                    # Track current container inside the worker
                    current_container_id = active_container_id

                    while True:
                        item = plot_queue.get()
                        if item is None:
                            break
                            
                        plot_prompt, q_index = item
                        try:
                            # Apply FinOps logic to background plots
                            if current_container_id:
                                container_config = current_container_id
                            else:
                                container_config = {"type": "auto", "memory_limit": memory_limit}

                            log_event("container_requested", {
                                "context": "quiz_background_plot",
                                "question_index": q_index,
                                "memory_limit": memory_limit,
                                "explicit_id": current_container_id
                            })
                            
                            bg_req = {
                                "model": active_config.model,
                                "input": [{"role": "user", "content": f"Generate a plot for this mathematical request: {plot_prompt}"}],
                                "tools": [{"type": "code_interpreter", "container": container_config}], 
                                "instructions": instructions
                            }
                            
                            response = bg_client.responses.create(**bg_req)

                            # Extract container ID if this was a brand new one
                            if not current_container_id:
                                output_list = getattr(response, "output", []) or []
                                for out_item in output_list:
                                    if getattr(out_item, "type", "") == "code_interpreter_call":
                                        cid = getattr(out_item, "container_id", None)
                                        if not cid and hasattr(out_item, "code_interpreter"):
                                            cid = getattr(out_item.code_interpreter, "container_id", None)
                                        if not cid and hasattr(out_item, "code_interpreter_call"):
                                            cid = getattr(out_item.code_interpreter_call, "container_id", None)
                                        if cid: 
                                            current_container_id = cid
                                            if actual_conversation_id and user_id:
                                                try:
                                                    ContainerUsageService().log_container_usage(
                                                        user_id=user_id,
                                                        session_id=actual_conversation_id,
                                                        container_id=cid,
                                                        memory_limit=memory_limit
                                                    )
                                                except Exception as e:
                                                    logger.error(f"Failed to save background container: {e}")
                                            break

                            uploaded_map = AiAssetsService.handle_generated_files(bg_client, response, folder="quiz_assets")
                            
                            if uploaded_map:
                                s3_url = list(uploaded_map.values())[0]
                                stream_manager.send_partial_image(index=q_index, b64_data=s3_url)
                                image_urls_map[q_index] = s3_url
                        except Exception as e:
                            logger.error(f"BG plot generation failed for index {q_index}: {e}")
                        finally:
                            plot_queue.task_done()

                plot_worker_thread = threading.Thread(target=_plot_worker)
                plot_worker_thread.start()

                for event in stream_gen:
                    evt_type = event.get("type")
                    if evt_type == "intro":
                        final_reply_text = event.get("text", "")
                    
                    elif evt_type == "image_request":
                        q_idx = event.get("index", 0)
                        if q_idx in allowed_visual_indices:
                            prompt_str = event.get("prompt", "")
                            t = threading.Thread(target=_bg_image_generator, args=(prompt_str, q_idx))
                            t.start()
                            image_threads.append(t)

                    elif evt_type == "plot_request":
                        q_idx = event.get("index", 0)
                        if q_idx in allowed_visual_indices:
                            prompt_str = event.get("prompt", "")
                            plot_queue.put((prompt_str, q_idx))

                    elif evt_type == "question":
                        q_data = event.get("data")
                        q_dict = q_data.dict() if hasattr(q_data, 'dict') else q_data
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
                        usage_data = event.get("data")
                        if actual_conversation_id:
                            cls._log_usage(usage_data, user_id, actual_conversation_id, mode)

                    elif evt_type == "done":
                        final_obj = event.get("full_response")
                        parsed_response = None
                        if hasattr(final_obj, 'questions'): parsed_response = final_obj
                        elif hasattr(final_obj, 'parsed') and hasattr(final_obj.parsed, 'questions'): parsed_response = final_obj.parsed
                        elif hasattr(final_obj, 'output_parsed') and hasattr(final_obj.output_parsed, 'questions'): parsed_response = final_obj.output_parsed
                        
                        if parsed_response:
                            final_reply_text = getattr(parsed_response, 'intro_message', final_reply_text)
                            accumulated_questions = [q.dict() if hasattr(q, 'dict') else q for q in parsed_response.questions]
                            
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
                    
                plot_queue.put(None)
                plot_worker_thread.join()
                    
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
                    mode=mode, exam_context=exam_context, requires_visuals=False, 
                    requires_creative_images=requires_creative_images, pdf_urls=clean_pdfs,
                    vector_store_ids=selected_vector_stores, web_search_config=web_search_config,
                    category=category
                )

                if usage_data and actual_conversation_id:
                    cls._log_usage(usage_data, user_id, actual_conversation_id, mode)

                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": getattr(quiz_model, 'title', 'Simulacro Generado'),
                    "questions": [q.dict() if hasattr(q, 'dict') else q for q in quiz_model.questions],
                    "question_count": len(quiz_model.questions),
                    "easier_payload": getattr(quiz_model, 'easier_payload', None),
                    "harder_payload": getattr(quiz_model, 'harder_payload', None),
                    "retry_payload": getattr(quiz_model, 'retry_payload', None)
                }
                
                for i, q_dict in enumerate(quiz_data["questions"]):
                    if i not in target_indices:
                        q_dict["image_prompt"] = None
                        q_dict["plot_prompt"] = None
                        q_dict["image_url"] = None

                final_reply_text = getattr(quiz_model, 'intro_message', "Aqui tienes tu simulacro.")

        except Exception as e:
            logger.error(f"Quiz Generation Error: {e}")
            log_event("quiz_generation_failed", {"error": str(e)}, level="error")
            final_reply_text = "**Error**: No pudimos generar el simulacro."
            quiz_data = None

        return final_reply_text, quiz_data