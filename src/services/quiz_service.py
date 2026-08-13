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
from src.config.exam_reasoning_doctrine import VISUAL_REASONING_DOCTRINE, ANALYTICAL_REASONING_DOCTRINE

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
        display_name: str = "General",
        num_questions: int = 5,
        format_map: Dict[int, str] = None,
        is_visual_subject: bool = False,
        is_creative_subject: bool = False,
        is_general_subject: bool = False,
        exam_context: str = "GENERAL",
        custom_topic: str = "",
        is_document_grounded: bool = False
    ) -> Dict[str, Any]:
        
        format_map = format_map or {}
        
        is_custom = is_document_grounded or bool(custom_topic.strip())
        active_display_name = custom_topic.strip().title() if custom_topic.strip() else display_name
        
        # 1. The Blueprint: Tell the AI exactly what format is required for each index
        format_instructions = "## 1. ARCHITECTURAL BLUEPRINT (FATAL ERROR IF IGNORED)\n"
        format_instructions += "You are bound by a hard-coded architectural matrix. For each question index, you MUST set `format_type` as follows:\n"
        for idx in range(num_questions):
            fmt = format_map.get(idx, "text_to_text")
            format_instructions += f"- Question {idx + 1} (Index {idx}): `format_type` = '{fmt}'\n"

        # 2. The Pre-Conditioning: Tell the AI what kind of question to design based on the format
        format_instructions += "\n## 2. FORMAT CONCEPTUALIZATION & MANDATORY FIELDS\n"
        format_instructions += "Based on the assigned `format_type`, you MUST design the question conceptually inside the `explanation` field before writing the question text or options:\n\n"
        
        format_instructions += (
            "A) If `image_to_image`:\n"
            "    - CONCEPT: A visual transformation or comparison.\n"
            "    - MANDATORY: The main question `plot_prompt` MUST NOT BE NULL. ALL FOUR options' `plot_prompt`s MUST NOT BE NULL. You must write natural language instructions for all 5.\n\n"
            
            "B) If `image_to_text`:\n"
            "    - CONCEPT: Visual interpretation (Analytical) or Environmental setting (Creative).\n"
            "    - MANDATORY: The main question visual MUST NOT BE NULL. You MUST populate EITHER `plot_prompt` OR `image_prompt` based on the active DOCTRINE below. The unselected field MUST remain null. The option visuals must remain null. You MUST NOT cheat by describing a graph in `context_text`.\n"
            "    - CRITICAL DECOUPLING ENFORCEMENT: If this is a creative/reading subject, the entire question, passage, and context data MUST be completely self-contained in text form. The visual must be purely ornamental and never contain text or information necessary to find the solution.\n\n"
            
            "C) If `text_to_image`:\n"
            "    - CONCEPT: Visual selection based on text data.\n"
            "    - MANDATORY: The main question visual is null. ALL FOUR options' `plot_prompt`s MUST NOT BE NULL.\n\n"
            
            "D) If `text_to_text`:\n"
            "   - CONCEPT: Standard analytical or theoretical question.\n"
            "   - MANDATORY: ALL `plot_prompt` and `image_prompt` fields MUST remain purely null.\n"
        )

        visual_doctrine = ""
        if is_visual_subject:
            visual_doctrine = (
                "CRITICAL BLINDNESS DOCTRINE (MATH/SCIENCE): Use `plot_prompt` for all required visuals. Keep `image_prompt` null. "
                "Design the stem visual to display only the input data plotted on standard Cartesian axes with visible coordinate numbers.\n"
            )
        elif is_creative_subject:
            visual_doctrine = (
                "CRITICAL AESTHETIC DOCTRINE (CREATIVE): Use `image_prompt` for stem visuals. Keep `plot_prompt` always null. "
                "You MUST absolutely BAN any mention of academic tropes (no notebooks, no whiteboards, no diagrams). "
                "CRITICAL VISUAL DECOUPLING: The visual generated from your `image_prompt` is strictly environmental and decorative. "
                "The quiz item must be 100% solvable using only the text inside `context_text` and `question_text`. "
                "NEVER attempt to embed text, reading blocks, infograms, timelines, or factual tables into the `image_prompt` for creative/reading categories.\n"
            )
        elif is_general_subject:
            visual_doctrine = (
                "CRITICAL AESTHETIC DOCTRINE (HYBRID): For stem visuals, select exactly ONE engine (`plot_prompt` for math/data, OR `image_prompt` for creative).\n"
            )

        # Psychometric parameters instructions with dynamic scaling
        if exam_context.upper() == "UNAL":
            if is_general_subject and not is_custom:
                psychometric_doctrine = (
                    "## 6. PSYCHOMETRIC EVALUATION METADATA (UNAL GLOBAL RASCH MODEL)\n"
                    "- `evaluation_metadata.exam_type` MUST be 'unal'.\n"
                    "- `evaluation_metadata.evaluation_level` MUST be 'global'.\n"
                    "- `evaluation_metadata.subject_category` MUST be 'Prueba de Admision UNAL'.\n"
                    "- `scale_config` MUST be: min_score=0, max_score=1000, mean=500, standard_deviation=100.\n"
                    "- `psychometric_params`: The UNAL exam uses the 1-Parameter Rasch model. Therefore, you MUST hardcode `a_discrimination` to exactly 1.0 and `c_guessing` to exactly 0.0. You must ONLY vary `b_difficulty` between -3.0 and 3.0 based on the cognitive complexity of the question.\n"
                )
            else:
                psychometric_doctrine = (
                    "## 6. PSYCHOMETRIC EVALUATION METADATA (UNAL COMPONENT RASCH MODEL)\n"
                    "- `evaluation_metadata.exam_type` MUST be 'unal'.\n"
                    "- `evaluation_metadata.evaluation_level` MUST be 'component'.\n"
                    f"- `evaluation_metadata.subject_category` MUST be '{active_display_name}'.\n"
                    "- `scale_config` MUST be: min_score=0, max_score=20, mean=10, standard_deviation=1.\n"
                    "- `psychometric_params`: The UNAL exam uses the 1-Parameter Rasch model. Therefore, you MUST hardcode `a_discrimination` to exactly 1.0 and `c_guessing` to exactly 0.0. You must ONLY vary `b_difficulty` between -3.0 and 3.0 based on the cognitive complexity of the question.\n"
                )
        else:
            if is_general_subject and not is_custom:
                psychometric_doctrine = (
                    "## 6. PSYCHOMETRIC EVALUATION METADATA (ICFES GLOBAL 3PL MODEL)\n"
                    "- `evaluation_metadata.exam_type` MUST be 'icfes'.\n"
                    "- `evaluation_metadata.evaluation_level` MUST be 'global'.\n"
                    "- `evaluation_metadata.subject_category` MUST be 'Competencias Integradas'.\n"
                    "- `scale_config` MUST be: min_score=0, max_score=500, mean=250, standard_deviation=50.\n"
                    "- `psychometric_params`: The ICFES exam uses the 3-Parameter Logistic (3PL) model. You must generate realistic psychometric parameters. `a_discrimination` between 0.5 and 2.5. `b_difficulty` between -3.0 (easy) and 3.0 (hard). `c_guessing` between 0.0 and 0.25.\n"
                )
            else:
                psychometric_doctrine = (
                    "## 6. PSYCHOMETRIC EVALUATION METADATA (ICFES COMPONENT 3PL MODEL)\n"
                    "- `evaluation_metadata.exam_type` MUST be 'icfes'.\n"
                    "- `evaluation_metadata.evaluation_level` MUST be 'component'.\n"
                    f"- `evaluation_metadata.subject_category` MUST be '{active_display_name}'.\n"
                    "- `scale_config` MUST be: min_score=0, max_score=100, mean=50, standard_deviation=10.\n"
                    "- `psychometric_params`: The ICFES exam uses the 3-Parameter Logistic (3PL) model. You must generate realistic psychometric parameters. `a_discrimination` between 0.5 and 2.5. `b_difficulty` between -3.0 (easy) and 3.0 (hard). `c_guessing` between 0.0 and 0.25.\n"
                )

        general_doctrine = ""
        if is_general_subject and not is_custom:
            if exam_context.upper() == "UNAL":
                domain_distribution = "Mathematics, Textual Analysis, Natural Sciences, Social Sciences, and Image Analysis"
            else:
                domain_distribution = "Mathematics, Critical Reading, Natural Sciences, Social Sciences, and English"
                
            general_doctrine = (
                "## 7. MULTI-SUBJECT DISTRIBUTION ENFORCEMENT (CRITICAL)\n"
                "The user requested a 'General' exam. You MUST generate an interdisciplinary test. "
                "You are FORBIDDEN from generating all questions for a single subject. "
                f"You MUST distribute the questions evenly across all core domains ({domain_distribution}). "
                "Force yourself to switch academic domains for every single question index.\n\n"
            )

        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION\n"
            f"The user requested a quiz/exam about '{active_display_name}'. Generate exactly {num_questions} distinct questions.\n\n"
            f"{format_instructions}\n"
            f"## 3. SUBJECT SPECIFIC DOCTRINES\n"
            f"{visual_doctrine}\n"
            "## 4. LOGIC PATHS & EXPLANATION\n"
            f"{ANALYTICAL_REASONING_DOCTRINE}\n\n"
            f"{VISUAL_REASONING_DOCTRINE}\n\n"
            "## 5. SCHEMA & FIELD RESTRICTIONS\n"
            "- SOURCES: Keep `source_url` null unless you hold a verified URL.\n"
            "- CONTEXT: Use `context_text` ONLY for large reading passages. NEVER use it to describe a graph that should be in a plot_prompt.\n"
            "- OPTION TEXT vs FEEDBACK: The `text` field in the options is the literal answer the student clicks. The `feedback` is the explanation. Do NOT put the answer inside the feedback and leave the text null. For `text_to_text` and `image_to_text` formats, the `text` field MUST BE POPULATED.\n\n"
            f"{psychometric_doctrine}\n"
            f"{general_doctrine}"
            "## SMART FOLLOW-UP PROTOCOL\n"
            "Generate 3 'Ghost Prompts' (easier_payload, harder_payload, retry_payload) in the EXACT SAME LANGUAGE as the quiz.\n"
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
        display_name: str = "General",
        attachments: List[Dict[str, str]] | None = None,
        actual_conversation_id: str | None = None,
        num_questions: int = 0,
        custom_topic: str = "",
        is_document_grounded: bool = False
    ) -> Tuple[str, Dict | None]:
        
        has_attachments = bool(attachments and len(attachments) > 0)
        is_doc_grounded = is_document_grounded or has_attachments
        
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
        image_to_text_indices = []
        text_to_image_indices = []
        image_to_image_indices = []

        if is_analisis_imagen:
            max_visuals = num_questions
            target_visuals = num_questions
            image_to_text_indices = list(range(num_questions))
        elif is_general_subject or is_visual_subject or is_creative_subject:
            max_visuals = math.floor(num_questions * 0.4)
            target_visuals = random.randint(0, max_visuals) if max_visuals > 0 else 0
            
            if target_visuals > 0:
                raw_indices = random.sample(range(num_questions), target_visuals)
                
                if is_creative_subject and not is_general_subject and not is_visual_subject:
                    image_to_text_indices = sorted(raw_indices)
                    text_to_image_indices = []
                    image_to_image_indices = []
                else:
                    num_stem = math.floor(target_visuals * 0.5)
                    num_opts = math.floor(target_visuals * 0.3)
                    
                    random.shuffle(raw_indices)
                    image_to_text_indices = sorted(raw_indices[:num_stem])
                    text_to_image_indices = sorted(raw_indices[num_stem:num_stem+num_opts])
                    image_to_image_indices = sorted(raw_indices[num_stem+num_opts:])

        allowed_stem_visuals = set(image_to_text_indices + image_to_image_indices)
        allowed_opt_visuals = set(text_to_image_indices + image_to_image_indices)

        # Build the strictly defined format map for the new Schema Architecture
        format_map = {}
        for i in range(num_questions):
            if i in image_to_text_indices:
                format_map[i] = "image_to_text"
            elif i in text_to_image_indices:
                format_map[i] = "text_to_image"
            elif i in image_to_image_indices:
                format_map[i] = "image_to_image"
            else:
                format_map[i] = "text_to_text"

        log_event("dynamic_visual_quota_calculated", {
            "subject_topic": topic_lower,
            "display_name": display_name,
            "custom_topic": custom_topic,
            "is_general_subject": is_general_subject,
            "is_visual_subject": is_visual_subject,
            "is_creative_subject": is_creative_subject,
            "is_document_grounded": is_doc_grounded,
            "num_questions_requested": num_questions,
            "target_visuals_enforced": target_visuals,
            "format_map": format_map
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
            display_name=display_name,
            num_questions=num_questions, 
            format_map=format_map,
            is_visual_subject=is_visual_subject,
            is_creative_subject=is_creative_subject,
            is_general_subject=is_general_subject,
            exam_context=exam_context,
            custom_topic=custom_topic,
            is_document_grounded=is_doc_grounded
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
                    requires_creative_images=requires_creative_images, attachments=attachments,
                    vector_store_ids=selected_vector_stores, web_search_config=web_search_config,
                    category=category, custom_topic=custom_topic, is_document_grounded=is_doc_grounded
                )
                
                seen_indices = set()
                accumulated_questions = []
                ai_generated_title = "Simulacro Generado" 
                parsed_response = None
                
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
                        if hasattr(final_obj, 'questions'): parsed_response = final_obj
                        elif hasattr(final_obj, 'parsed') and hasattr(final_obj.parsed, 'questions'): parsed_response = final_obj.parsed
                        elif hasattr(final_obj, 'output_parsed') and hasattr(final_obj.output_parsed, 'questions'): parsed_response = final_obj.output_parsed
                        
                        if parsed_response:
                            final_reply_text = getattr(parsed_response, 'intro_message', final_reply_text)
                            accumulated_questions = [q.dict() if hasattr(q, 'dict') else q for q in parsed_response.questions]
                            
                            for i, q_dict in enumerate(accumulated_questions):
                                if i not in allowed_stem_visuals:
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

                evaluation_metadata = None
                if parsed_response and hasattr(parsed_response, 'evaluation_metadata'):
                    meta_obj = parsed_response.evaluation_metadata
                    evaluation_metadata = meta_obj.dict() if hasattr(meta_obj, 'dict') else meta_obj

                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": ai_generated_title,
                    "evaluation_metadata": evaluation_metadata,
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
                    requires_creative_images=requires_creative_images, attachments=attachments,
                    vector_store_ids=selected_vector_stores, web_search_config=web_search_config,
                    category=category, custom_topic=custom_topic, is_document_grounded=is_doc_grounded
                )

                if usage_data and actual_conversation_id:
                    cls._log_usage(usage_data, user_id, actual_conversation_id, mode)

                meta_obj = getattr(quiz_model, 'evaluation_metadata', None)
                evaluation_metadata = meta_obj.dict() if hasattr(meta_obj, 'dict') else meta_obj

                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": getattr(quiz_model, 'title', 'Simulacro Generado'),
                    "evaluation_metadata": evaluation_metadata,
                    "questions": [q.dict() if hasattr(q, 'dict') else q for q in quiz_model.questions],
                    "question_count": len(quiz_model.questions),
                    "easier_payload": getattr(quiz_model, 'easier_payload', None),
                    "harder_payload": getattr(quiz_model, 'harder_payload', None),
                    "retry_payload": getattr(quiz_model, 'retry_payload', None)
                }
                
                for i, q_dict in enumerate(quiz_data["questions"]):
                    if i not in allowed_stem_visuals:
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