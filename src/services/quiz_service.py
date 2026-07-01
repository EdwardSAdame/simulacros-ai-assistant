# FILE: src/services/quiz_service.py
from typing import Dict, Any, List, Tuple
import math
import random
import base64
import logging

from src.utils.logging_utils import log_event
from src.services.storage_service import storage_service
from src.assistant.assistant_client import generate_structured_quiz, stream_structured_quiz
from src.config.page_vectorstores import get_stores_for_page
from src.config.web_search_config import get_search_filters
from src.config.model_config import get_model_config 
from src.services.token_usage_service import TokenUsageService
from src.services.container_usage_service import ContainerUsageService

from src.assistant.clients.base_client import BaseAssistantClient
from src.services.visual_worker_service import VisualWorkerService
from src.config.visual_instructions import VISUAL_REASONING_DOCTRINE

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
    def _log_usage(usage_data: dict, current_user: str | None, conversation_id: str, active_mode: str):
        if not usage_data or not current_user: return
        try:
            active_config = get_model_config(active_mode)
            engine_name = active_config.model
            
            usage_dict = BaseAssistantClient.extract_usage_metrics(usage_data)

            TokenUsageService().log_token_usage(
                user_id=current_user,
                conversation_id=conversation_id, 
                source="quiz",                
                tier=active_mode,   
                engine=engine_name, 
                input_tokens=usage_dict["input_tokens"],
                output_tokens=usage_dict["output_tokens"],
                total_tokens=usage_dict["total_tokens"],
                reasoning_tokens=usage_dict["reasoning_tokens"],
                cached_tokens=usage_dict["cached_tokens"]
            )
        except Exception as e:
            logger.error(f"Failed to log token usage in quiz service: {e}")

    @staticmethod
    def get_system_instruction(
        topic: str = "general", 
        num_questions: int = 5,
        stem_indices: List[int] = None,
        opt_indices: List[int] = None,
        hyb_indices: List[int] = None,
        is_general_subject: bool = False,
        is_visual_subject: bool = False,
        is_creative_subject: bool = False
    ) -> Dict[str, Any]:
        
        stem_indices = stem_indices or []
        opt_indices = opt_indices or []
        hyb_indices = hyb_indices or []
        
        target_visuals = len(stem_indices) + len(opt_indices) + len(hyb_indices)
        
        stem_human = [i + 1 for i in stem_indices]
        opt_human = [i + 1 for i in opt_indices]
        hyb_human = [i + 1 for i in hyb_indices]

        visual_instruction = ""

        if target_visuals > 0:
            if is_general_subject:
                visual_instruction = "## VISUAL GENERATION PROTOCOL (HYBRID MULTI-SUBJECT - MANDATORY)\n"
            elif is_visual_subject:
                visual_instruction = "## VISUAL GENERATION PROTOCOL (DATA GRAPHS - MANDATORY)\n"
            elif is_creative_subject:
                visual_instruction = "## VISUAL GENERATION PROTOCOL (CREATIVE ILLUSTRATIONS - MANDATORY)\n"
                
            visual_instruction += f"Generate EXACTLY {target_visuals} visual question(s).\n"
            visual_instruction += "DETERMINISTIC DISTRIBUTION ENFORCEMENT:\n"
            
            if stem_human:
                visual_instruction += f"- BUCKET A (Stem Visual Only): For question numbers {stem_human}, write a visual prompt (`plot_prompt` or `image_prompt`) for the QUESTION STEM ONLY. Leave all option visuals null.\n"
            if opt_human:
                visual_instruction += f"- BUCKET B (Option Visuals Only): For question numbers {opt_human}, leave the stem visual null. Write a mathematical description in `plot_prompt` for EVERY option AND set the `text` field for every option to a literal JSON null.\n"
            if hyb_human:
                visual_instruction += f"- BUCKET C (Hybrid Visuals): For question numbers {hyb_human}, write a visual prompt for the QUESTION STEM AND a `plot_prompt` for EVERY option. Set the `text` field for every option to a literal JSON null. Design the Stem Visual to display only the initial state or input parameters. Reserve the final outcome exclusively for the Option Visuals.\n"
                
            visual_instruction += "For the remaining questions not listed above, set ALL visual fields (stem and options) to a literal JSON null.\n\n"
            
            if is_visual_subject:
                visual_instruction += "CRITICAL: For stem visuals, use `plot_prompt`. Keep `image_prompt` and `visual_metaphor_planning` null. Write mathematical instructions strictly as plain English/Spanish.\n"
                visual_instruction += "CRITICAL BLINDNESS DOCTRINE: Design the stem visual to display only the input data plotted on standard Cartesian axes with visible coordinate numbers. Reserve the derived answers for the options.\n"
            elif is_creative_subject:
                visual_instruction += "CRITICAL: For stem visuals, use `visual_metaphor_planning` and `image_prompt`. Keep `plot_prompt` always null.\n"
                visual_instruction += "CRITICAL CREATIVE DOCTRINE: For creative subjects, ensure the options are purely text.\n"
                visual_instruction += "CRITICAL DECORATIVE DOCTRINE: The `image_prompt` is a decorative background. Ensure the question logic relies entirely on the `context_text` or reading comprehension.\n"
                visual_instruction += "CRITICAL METAPHOR DOCTRINE: For `visual_metaphor_planning` and `image_prompt`, be extremely concise. Identify the broad academic domain and describe a generic, static physical scene.\n"
            elif is_general_subject:
                visual_instruction += "CRITICAL: For stem visuals, select exactly ONE engine (`plot_prompt` for math/data, OR `visual_metaphor_planning` + `image_prompt` for creative). Keep the other null.\n"
                visual_instruction += "CRITICAL DECORATIVE DOCTRINE: If you use `image_prompt`, use `visual_metaphor_planning` first to describe a physical scene.\n"
                visual_instruction += "CRITICAL METAPHOR DOCTRINE: If using `image_prompt`, describe a generic physical scene.\n"
                
        else:
            visual_instruction = (
                "## VISUAL & TOOL EXECUTION PROTOCOL (TEXT ONLY)\n"
                "Produce a strictly text-based quiz. Keep `image_url`, `visual_metaphor_planning`, `image_prompt`, and all `plot_prompt`s strictly as literal JSON null.\n\n"
            )

        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION\n"
            f"The user requested a quiz/exam about '{topic}'. "
            f"Generate exactly {num_questions} distinct questions.\n\n"
            f"{visual_instruction}"
            "## DUAL-ENGINE LOGIC TRACKS\n"
            "Choose your internal logic engine based strictly on the required option format (Text vs Image).\n\n"
            "### ENGINE 1: THE ANALYTICAL ENGINE (Use for Text-Only Options)\n"
            "If the options are TEXT, calculate a specific numerical or factual answer.\n"
            "1. **SETUP**: Define the exact variables, facts, or numbers to be used.\n"
            "2. **SOLUTION**: Explicitly calculate the step-by-step arithmetic or logical derivation.\n"
            "3. **TRAPS**: Generate 3 wrong answers based on common computational errors, incorrect formulas, or factual misunderstandings.\n"
            "4. **QUESTION**: Ask for a specific calculated or derived value.\n\n"
            f"{VISUAL_REASONING_DOCTRINE}\n\n"
            "## SCHEMA & FIELD RESTRICTIONS\n"
            "- **SOURCES**: Keep `source_url` as null unless you actively hold a verified URL in your context.\n"
            "- **CONTEXT**: Use `context_text` ONLY if the question requires a large foundational reading passage or shared scenario. Otherwise, keep it null.\n"
            "- **OPTION VISUALS**: If an option has a `plot_prompt`, its `text` field MUST be null.\n\n"
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
        actual_conversation_id: str | None = None,
        num_questions: int = 0
    ) -> Tuple[str, Dict | None]:
        
        topic_hint = category if category else "General Knowledge"
        
        if num_questions < 1:
            num_questions = random.randint(12, 17)
        elif num_questions > 45:
            num_questions = 45

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
        is_analisis_imagen = "analisis_imagen" in topic_lower
        
        requires_creative_images = is_creative_subject or is_general_subject

        max_visuals = 0
        target_visuals = 0
        stem_visual_indices = []
        options_visual_indices = []
        hybrid_visual_indices = []

        if is_analisis_imagen:
            max_visuals = num_questions
            target_visuals = num_questions
            stem_visual_indices = list(range(num_questions))
        elif is_general_subject or is_visual_subject or is_creative_subject:
            max_visuals = math.floor(num_questions * 0.4)
            target_visuals = random.randint(0, max_visuals) if max_visuals > 0 else 0
            
            if target_visuals > 0:
                raw_indices = random.sample(range(num_questions), target_visuals)
                
                if is_creative_subject and not is_general_subject and not is_visual_subject:
                    stem_visual_indices = sorted(raw_indices)
                    options_visual_indices = []
                    hybrid_visual_indices = []
                else:
                    num_stem = math.floor(target_visuals * 0.5)
                    num_opts = math.floor(target_visuals * 0.3)
                    
                    random.shuffle(raw_indices)
                    stem_visual_indices = sorted(raw_indices[:num_stem])
                    options_visual_indices = sorted(raw_indices[num_stem:num_stem+num_opts])
                    hybrid_visual_indices = sorted(raw_indices[num_stem+num_opts:])

        allowed_stem_visuals = set(stem_visual_indices + hybrid_visual_indices)
        allowed_opt_visuals = set(options_visual_indices + hybrid_visual_indices)

        log_event("dynamic_visual_quota_calculated", {
            "subject_topic": topic_lower,
            "is_general_subject": is_general_subject,
            "is_visual_subject": is_visual_subject,
            "is_creative_subject": is_creative_subject,
            "num_questions_requested": num_questions,
            "target_visuals_enforced": target_visuals,
            "stem_indices": stem_visual_indices,
            "options_indices": options_visual_indices,
            "hybrid_indices": hybrid_visual_indices
        })

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
            stem_indices=stem_visual_indices,
            opt_indices=options_visual_indices,
            hyb_indices=hybrid_visual_indices,
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
                
                worker = VisualWorkerService(
                    mode=mode,
                    user_id=user_id,
                    conversation_id=actual_conversation_id,
                    stream_manager=stream_manager,
                    active_container_id=active_container_id
                )
                worker.start_plot_worker()

                for event in stream_gen:
                    evt_type = event.get("type")
                    if evt_type == "intro":
                        final_reply_text = event.get("text", "")
                    
                    elif evt_type == "image_request":
                        q_idx = event.get("index", 0)
                        if q_idx in allowed_stem_visuals:
                            worker.spawn_image_worker(event.get("prompt", ""), q_idx)

                    elif evt_type == "plot_request":
                        q_idx = event.get("index", 0)
                        opt_idx = event.get("opt_index", None)
                        
                        is_allowed = False
                        if opt_idx is None and q_idx in allowed_stem_visuals:
                            is_allowed = True
                        elif opt_idx is not None and q_idx in allowed_opt_visuals:
                            is_allowed = True

                        if is_allowed:
                            worker.enqueue_plot(event.get("prompt", ""), q_idx, opt_idx)

                    elif evt_type == "question":
                        q_data = event.get("data")
                        q_dict = q_data.dict() if hasattr(q_data, 'dict') else q_data
                        idx = event.get("index", 0)
                        
                        if idx not in allowed_stem_visuals:
                            q_dict["visual_metaphor_planning"] = None
                            q_dict["image_prompt"] = None
                            q_dict["plot_prompt"] = None
                            q_dict["image_url"] = None
                            
                        if idx not in allowed_opt_visuals:
                            for opt in q_dict.get("options", []):
                                if isinstance(opt, dict):
                                    opt["plot_prompt"] = None
                                    opt["image_url"] = None

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
                                stream_manager.send_partial_image(index=event.get("index", 0), b64_data=s3_url, opt_index=None)
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
                                if i not in allowed_stem_visuals:
                                    q_dict["visual_metaphor_planning"] = None
                                    q_dict["image_prompt"] = None
                                    q_dict["plot_prompt"] = None
                                    q_dict["image_url"] = None
                                    
                                if i not in allowed_opt_visuals:
                                    for opt in q_dict.get("options", []):
                                        if isinstance(opt, dict):
                                            opt["plot_prompt"] = None
                                            opt["image_url"] = None
                            
                            if hasattr(parsed_response, 'title') and parsed_response.title:
                                ai_generated_title = parsed_response.title
                            
                            if hasattr(parsed_response, 'easier_payload'): ghost_easier = parsed_response.easier_payload
                            if hasattr(parsed_response, 'harder_payload'): ghost_harder = parsed_response.harder_payload
                            if hasattr(parsed_response, 'retry_payload'): ghost_retry = parsed_response.retry_payload

                    elif evt_type == "error":
                        error_msg = event.get("error", "Unknown stream error")
                        stream_manager.send_error(error_msg)

                worker.shutdown_and_wait()
                    
                for i, q in enumerate(accumulated_questions):
                    if (i, None) in worker.image_urls_map:
                        q["image_url"] = worker.image_urls_map[(i, None)]
                    
                    for o_idx, opt in enumerate(q.get("options", [])):
                        if isinstance(opt, dict) and (i, o_idx) in worker.image_urls_map:
                            opt["image_url"] = worker.image_urls_map[(i, o_idx)]

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
                    if i not in allowed_stem_visuals:
                        q_dict["visual_metaphor_planning"] = None
                        q_dict["image_prompt"] = None
                        q_dict["plot_prompt"] = None
                        q_dict["image_url"] = None
                        
                    if i not in allowed_opt_visuals:
                        for opt in q_dict.get("options", []):
                            if isinstance(opt, dict):
                                opt["plot_prompt"] = None
                                opt["image_url"] = None

                final_reply_text = getattr(quiz_model, 'intro_message', "Aqui tienes tu simulacro.")

        except Exception as e:
            logger.error(f"Quiz Generation Error: {e}")
            log_event("quiz_generation_failed", {"error": str(e)}, level="error")
            final_reply_text = "**Error**: No pudimos generar el simulacro."
            quiz_data = None

        return final_reply_text, quiz_data