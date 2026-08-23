# src/services/quiz_service.py
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
        
        # 1. The Grouping Architecture: Dictate the Parent-Child Permutations
        grouping_instructions = "## 1. GROUP ARCHITECTURE & PERMUTATIONS (CRITICAL)\n"
        grouping_instructions += "You operate on a polymorphic, hierarchical schema. ALL questions must be wrapped inside `QuestionGroup` objects.\n"
        
        if is_creative_subject and not is_general_subject:
            grouping_instructions += (
                "SCENARIO A: SHARED CONTEXT (Nested Architecture)\n"
                "This is a reading-heavy subject requiring shared stimulus blocks.\n"
                "1. For EACH group you create, populate `context_text` with a unique reading passage.\n"
                "2. If the passage requires a visual, populate `group_image_prompt` or `group_plot_prompt`. If not, leave them null.\n"
                "3. Attach 3 to 5 dependent `QuizQuestion` objects inside that group's `questions` array.\n"
                f"4. Continue creating new groups until you reach exactly {num_questions} total questions across all groups.\n"
                "CRITICAL: Do NOT duplicate the shared reading passage inside the individual child questions.\n\n"
            )
        else:
            grouping_instructions += (
                "SCENARIO B: ISOLATED QUESTIONS (1-on-1 Architecture)\n"
                "This is an analytical or mixed exam where questions are independent.\n"
                "1. Each `QuestionGroup` MUST contain EXACTLY 1 `QuizQuestion`.\n"
                "2. The parent group is merely a structural wrapper. You MUST leave the parent's `group_title`, `context_text`, `group_image_prompt`, and `group_plot_prompt` strictly null.\n"
                f"3. Generate exactly {num_questions} groups, resulting in exactly {num_questions} total questions.\n\n"
            )

        # 2. The Blueprint
        format_instructions = "## 2. ARCHITECTURAL BLUEPRINT (FATAL ERROR IF IGNORED)\n"
        format_instructions += "You are bound by a hard-coded architectural matrix for the global question indices. For each overall question index, you MUST set the child's `format_type` as follows:\n"
        for idx in range(num_questions):
            fmt = format_map.get(idx, "text_to_text")
            format_instructions += f"- Global Question Index {idx}: `format_type` = '{fmt}'\n"

        # 3. The Pre-Conditioning: Child Independence
        format_instructions += "\n## 3. FORMAT CONCEPTUALIZATION & CHILD INDEPENDENCE\n"
        format_instructions += (
            "IMPORTANT: The assigned `format_type` dictates the visual behavior of the CHILD `QuizQuestion` ONLY. "
            "It is completely independent of the parent group's shared context visuals. Based on the `format_type`, design the child question:\n\n"
            
            "A) If `image_to_image`:\n"
            "    - CONCEPT: A visual transformation or comparison.\n"
            "    - MANDATORY: The child `plot_prompt` MUST NOT BE NULL. ALL FOUR options' `plot_prompt`s MUST NOT BE NULL.\n\n"
            
            "B) If `image_to_text`:\n"
            "    - CONCEPT: Visual interpretation or Environmental setting specific to this question.\n"
            "    - MANDATORY: The child question visual MUST NOT BE NULL. Populate EITHER `plot_prompt` OR `image_prompt`. Option visuals must remain null.\n\n"
            
            "C) If `text_to_image`:\n"
            "    - CONCEPT: Visual selection based on text data.\n"
            "    - MANDATORY: The child question visual is null. ALL FOUR options' `plot_prompt`s MUST NOT BE NULL.\n\n"
            
            "D) If `text_to_text`:\n"
            "   - CONCEPT: Standard analytical or theoretical question.\n"
            "   - MANDATORY: ALL child `plot_prompt` and `image_prompt` fields MUST remain purely null.\n"
        )

        visual_doctrine = ""
        if is_visual_subject:
            visual_doctrine = (
                "CRITICAL BLINDNESS DOCTRINE (MATH/SCIENCE): Use `plot_prompt` for all required visuals. Keep `image_prompt` null. "
                "Design visuals to display only input data plotted on Cartesian axes with visible coordinate numbers.\n"
            )
        elif is_creative_subject:
            visual_doctrine = (
                "CRITICAL AESTHETIC DOCTRINE (CREATIVE): Use `image_prompt` for stem visuals. Keep `plot_prompt` always null. "
                "You MUST absolutely BAN any mention of academic tropes (no notebooks, no whiteboards). "
                "CRITICAL VISUAL DECOUPLING: Visuals must be strictly environmental and decorative. "
                "NEVER attempt to embed text, reading blocks, or factual tables into the `image_prompt` or `group_image_prompt`.\n"
            )
        elif is_general_subject:
            visual_doctrine = (
                "CRITICAL AESTHETIC DOCTRINE (HYBRID): For visuals, select exactly ONE engine (`plot_prompt` for math/data, OR `image_prompt` for creative).\n"
            )

        if exam_context.upper() == "UNAL":
            if is_general_subject and not is_custom:
                psychometric_doctrine = (
                    "## 7. PSYCHOMETRIC EVALUATION METADATA (UNAL GLOBAL RASCH MODEL)\n"
                    "- `evaluation_metadata.exam_type` MUST be 'unal'.\n"
                    "- `evaluation_metadata.evaluation_level` MUST be 'global'.\n"
                    "- `evaluation_metadata.subject_category` MUST be 'Prueba de Admision UNAL'.\n"
                    "- `scale_config` MUST be: min_score=0, max_score=1000, mean=500, standard_deviation=100.\n"
                    "- `psychometric_params`: The UNAL exam uses the 1-Parameter Rasch model. Therefore, you MUST hardcode `a_discrimination` to exactly 1.0 and `c_guessing` to exactly 0.0. You must ONLY vary `b_difficulty` between -3.0 and 3.0 based on the cognitive complexity of the question.\n"
                )
            else:
                psychometric_doctrine = (
                    "## 7. PSYCHOMETRIC EVALUATION METADATA (UNAL COMPONENT RASCH MODEL)\n"
                    "- `evaluation_metadata.exam_type` MUST be 'unal'.\n"
                    "- `evaluation_metadata.evaluation_level` MUST be 'component'.\n"
                    f"- `evaluation_metadata.subject_category` MUST be '{active_display_name}'.\n"
                    "- `scale_config` MUST be: min_score=0, max_score=20, mean=10, standard_deviation=1.\n"
                    "- `psychometric_params`: The UNAL exam uses the 1-Parameter Rasch model. Therefore, you MUST hardcode `a_discrimination` to exactly 1.0 and `c_guessing` to exactly 0.0. You must ONLY vary `b_difficulty` between -3.0 and 3.0 based on the cognitive complexity of the question.\n"
                )
        else:
            if is_general_subject and not is_custom:
                psychometric_doctrine = (
                    "## 7. PSYCHOMETRIC EVALUATION METADATA (ICFES GLOBAL 3PL MODEL)\n"
                    "- `evaluation_metadata.exam_type` MUST be 'icfes'.\n"
                    "- `evaluation_metadata.evaluation_level` MUST be 'global'.\n"
                    "- `evaluation_metadata.subject_category` MUST be 'Competencias Integradas'.\n"
                    "- `scale_config` MUST be: min_score=0, max_score=500, mean=250, standard_deviation=50.\n"
                    "- `psychometric_params`: The ICFES exam uses the 3-Parameter Logistic (3PL) model. You must generate realistic psychometric parameters. `a_discrimination` between 0.5 and 2.5. `b_difficulty` between -3.0 (easy) and 3.0 (hard). `c_guessing` between 0.0 and 0.25.\n"
                )
            else:
                psychometric_doctrine = (
                    "## 7. PSYCHOMETRIC EVALUATION METADATA (ICFES COMPONENT 3PL MODEL)\n"
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
                "## 8. MULTI-SUBJECT DISTRIBUTION ENFORCEMENT (CRITICAL)\n"
                "The user requested a 'General' exam. You MUST generate an interdisciplinary test. "
                "You are FORBIDDEN from generating all questions for a single subject. "
                f"You MUST distribute the questions evenly across all core domains ({domain_distribution}). "
                "Force yourself to switch academic domains logically.\n\n"
            )

        instruction_text = (
            f"## IMMEDIATE RUNTIME MISSION\n"
            f"The user requested a quiz/exam about '{active_display_name}'. You must generate exactly {num_questions} questions in total.\n\n"
            f"{grouping_instructions}\n"
            f"{format_instructions}\n"
            f"## 4. SUBJECT SPECIFIC DOCTRINES\n"
            f"{visual_doctrine}\n"
            "## 5. LOGIC PATHS & EXPLANATION\n"
            f"{ANALYTICAL_REASONING_DOCTRINE}\n\n"
            f"{VISUAL_REASONING_DOCTRINE}\n\n"
            "## 6. SCHEMA & FIELD RESTRICTIONS\n"
            "- SOURCES: Keep `source_url` null unless you hold a verified URL.\n"
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
                        is_group_level = event.get("is_group_level", False)
                        if is_group_level:
                            g_idx = event.get("group_index", 0)
                            worker.spawn_image_worker(event.get("prompt", ""), f"group_{g_idx}")
                        else:
                            q_idx = event.get("index", 0)
                            if q_idx in allowed_stem_visuals:
                                worker.spawn_image_worker(event.get("prompt", ""), q_idx)

                    elif evt_type == "plot_request":
                        is_group_level = event.get("is_group_level", False)
                        if is_group_level:
                            g_idx = event.get("group_index", 0)
                            worker.enqueue_plot(event.get("prompt", ""), f"group_{g_idx}", None)
                        else:
                            q_idx = event.get("index", 0)
                            opt_idx = event.get("opt_index", None)
                            
                            is_allowed = False
                            if opt_idx is None and q_idx in allowed_stem_visuals:
                                is_allowed = True
                            elif opt_idx is not None and q_idx in allowed_opt_visuals:
                                is_allowed = True

                            if is_allowed:
                                worker.enqueue_plot(event.get("prompt", ""), q_idx, opt_idx)

                    elif evt_type == "group_start":
                        stream_manager.send_group_start(
                            group_index=event.get("group_index", 0),
                            group_title=event.get("group_title"),
                            context_text=event.get("context_text"),
                            group_source_url=event.get("group_source_url")
                        )

                    elif evt_type == "question":
                        q_data = event.get("data")
                        
                        # Determine if data is a Pydantic model and safely dump to dictionary
                        if hasattr(q_data, 'model_dump'):
                            q_dict = q_data.model_dump()
                        elif hasattr(q_data, 'dict'):
                            q_dict = q_data.dict()
                        else:
                            # It is a partial dict from ijson, create a shallow copy to prevent mutation
                            q_dict = dict(q_data)
                            
                        idx = event.get("index", 0)
                        group_idx = event.get("group_index", 0)
                        
                        # Prevent inflating partial WebSocket typing events with null visual keys
                        is_full_question = "options" in q_dict
                        
                        if is_full_question:
                            if idx not in allowed_stem_visuals:
                                q_dict["image_prompt"] = None
                                q_dict["plot_prompt"] = None
                                q_dict["image_url"] = None
                                
                            if idx not in allowed_opt_visuals:
                                for opt in q_dict.get("options", []):
                                    if isinstance(opt, dict):
                                        opt["plot_prompt"] = None
                                        opt["image_url"] = None

                        stream_manager.send_quiz_item(question_data=q_dict, index=idx, group_index=group_idx)
                            
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
                        if hasattr(final_obj, 'groups'): parsed_response = final_obj
                        elif hasattr(final_obj, 'parsed') and hasattr(final_obj.parsed, 'groups'): parsed_response = final_obj.parsed
                        elif hasattr(final_obj, 'output_parsed') and hasattr(final_obj.output_parsed, 'groups'): parsed_response = final_obj.output_parsed
                        
                        if parsed_response:
                            final_reply_text = getattr(parsed_response, 'intro_message', final_reply_text)
                            
                            if hasattr(parsed_response, 'title') and parsed_response.title:
                                ai_generated_title = parsed_response.title
                            
                            if hasattr(parsed_response, 'easier_payload'): ghost_easier = parsed_response.easier_payload
                            if hasattr(parsed_response, 'harder_payload'): ghost_harder = parsed_response.harder_payload
                            if hasattr(parsed_response, 'retry_payload'): ghost_retry = parsed_response.retry_payload

                    elif evt_type == "error":
                        error_msg = event.get("error", "Unknown stream error")
                        stream_manager.send_error(error_msg)

                worker.shutdown_and_wait()

                # Reconstruct and map data safely from the final parsed output
                accumulated_groups = []
                total_questions = 0
                evaluation_metadata = None
                
                if parsed_response:
                    if hasattr(parsed_response, 'evaluation_metadata'):
                        meta_obj = parsed_response.evaluation_metadata
                        if hasattr(meta_obj, 'model_dump'):
                            evaluation_metadata = meta_obj.model_dump()
                        elif hasattr(meta_obj, 'dict'):
                            evaluation_metadata = meta_obj.dict()
                        else:
                            evaluation_metadata = meta_obj

                    accumulated_groups = []
                    for g in parsed_response.groups:
                        if hasattr(g, 'model_dump'):
                            accumulated_groups.append(g.model_dump())
                        elif hasattr(g, 'dict'):
                            accumulated_groups.append(g.dict())
                        else:
                            accumulated_groups.append(g)
                    
                    global_q_idx = 0
                    for g_idx, group in enumerate(accumulated_groups):
                        # Safely initialize group image URL before mapping
                        group["group_image_url"] = group.get("group_image_url")
                        
                        # Reconstruct group-level image URLs
                        group_key = (f"group_{g_idx}", None)
                        if group_key in worker.image_urls_map:
                            group["group_image_url"] = worker.image_urls_map[group_key]

                        for q_dict in group.get("questions", []):
                            # Wipe unauthorized child visuals using the global index mapping
                            if global_q_idx not in allowed_stem_visuals:
                                q_dict["image_prompt"] = None
                                q_dict["plot_prompt"] = None
                                q_dict["image_url"] = None
                                
                            if global_q_idx not in allowed_opt_visuals:
                                for opt in q_dict.get("options", []):
                                    if isinstance(opt, dict):
                                        opt["plot_prompt"] = None
                                        opt["image_url"] = None

                            # Assign resolved image URLs from worker using global child index
                            if (global_q_idx, None) in worker.image_urls_map:
                                q_dict["image_url"] = worker.image_urls_map[(global_q_idx, None)]
                            
                            for o_idx, opt in enumerate(q_dict.get("options", [])):
                                if isinstance(opt, dict) and (global_q_idx, o_idx) in worker.image_urls_map:
                                    opt["image_url"] = worker.image_urls_map[(global_q_idx, o_idx)]
                            
                            global_q_idx += 1
                    
                    total_questions = global_q_idx

                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": ai_generated_title,
                    "evaluation_metadata": evaluation_metadata,
                    "groups": accumulated_groups,
                    "question_count": total_questions,
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
                if hasattr(meta_obj, 'model_dump'):
                    evaluation_metadata = meta_obj.model_dump()
                elif hasattr(meta_obj, 'dict'):
                    evaluation_metadata = meta_obj.dict()
                else:
                    evaluation_metadata = meta_obj
                
                accumulated_groups = []
                for g in quiz_model.groups:
                    if hasattr(g, 'model_dump'):
                        accumulated_groups.append(g.model_dump())
                    elif hasattr(g, 'dict'):
                        accumulated_groups.append(g.dict())
                    else:
                        accumulated_groups.append(g)

                global_q_idx = 0
                for group in accumulated_groups:
                    group["group_image_url"] = group.get("group_image_url")
                    
                    for q_dict in group.get("questions", []):
                        if global_q_idx not in allowed_stem_visuals:
                            q_dict["image_prompt"] = None
                            q_dict["plot_prompt"] = None
                            q_dict["image_url"] = None
                            
                        if global_q_idx not in allowed_opt_visuals:
                            for opt in q_dict.get("options", []):
                                if isinstance(opt, dict):
                                    opt["plot_prompt"] = None
                                    opt["image_url"] = None
                        global_q_idx += 1

                quiz_data = {
                    "quiz_mode": "batch", 
                    "topic": getattr(quiz_model, 'title', 'Simulacro Generado'),
                    "evaluation_metadata": evaluation_metadata,
                    "groups": accumulated_groups,
                    "question_count": global_q_idx,
                    "easier_payload": getattr(quiz_model, 'easier_payload', None),
                    "harder_payload": getattr(quiz_model, 'harder_payload', None),
                    "retry_payload": getattr(quiz_model, 'retry_payload', None)
                }

                final_reply_text = getattr(quiz_model, 'intro_message', "Aqui tienes tu simulacro.")

        except Exception as e:
            logger.error(f"Quiz Generation Error: {e}")
            log_event("quiz_generation_failed", {"error": str(e)}, level="error")
            final_reply_text = "**Error**: No pudimos generar el simulacro."
            quiz_data = None

        return final_reply_text, quiz_data