# src/services/chat_service.py
import logging
import concurrent.futures
from typing import Tuple, Dict, Any, List

# CONFIG
from src.config.settings import get_vector_search_max_results, get_code_interpreter_memory
from src.config.page_vectorstores import get_stores_for_page
from src.config.model_config import get_model_config
from src.utils.logging_utils import log_event

# SERVICES
from src.services.context_builder import build_runtime_context
from src.services.arena_service import arena_service
from src.config.system_instructions import build_system_instructions
from src.assistant.assistant_client import (
    send_message_to_assistant,
    generate_plot_blueprint,
    execute_plot_generation
)
from src.services.token_usage_service import TokenUsageService
from src.services.container_usage_service import ContainerUsageService

logger = logging.getLogger(__name__)

class ChatService:
    """
    Handles standard conversational AI interactions, including custom Arena 
    context injection, and high-performance parallel visualization generation.
    """

    @staticmethod
    def _log_usage(usage_data: dict, current_user: str | None, conversation_id: str, active_mode: str):
        if not usage_data or not current_user: return
        try:
            active_config = get_model_config(active_mode)
            engine_name = active_config.model

            input_val = usage_data.get("input_tokens", usage_data.get("prompt_tokens", 0))
            output_val = usage_data.get("output_tokens", usage_data.get("completion_tokens", 0))

            TokenUsageService().log_token_usage(
                user_id=current_user,
                conversation_id=conversation_id, 
                source="chat",                   
                tier=active_mode,   
                engine=engine_name, 
                input_tokens=input_val,
                output_tokens=output_val,
                total_tokens=usage_data.get("total_tokens", 0),
                reasoning_tokens=usage_data.get("reasoning_tokens", 0),
                cached_tokens=usage_data.get("cached_tokens", 0)
            )
        except Exception as e:
            logger.error(f"Failed to log token usage: {e}")

    @staticmethod
    def _log_container(user_id: str | None, conversation_id: str, container_id: str | None):
        if not user_id or not container_id: 
            return
        try:
            memory_limit = get_code_interpreter_memory()
            ContainerUsageService().log_container_usage(
                user_id=user_id,
                conversation_id=conversation_id,
                container_id=container_id,
                source="chat", 
                memory_limit=memory_limit
            )
        except Exception as e:
            logger.error(f"Failed to log container usage: {e}")

    @classmethod
    def execute_standard_chat(
        cls,
        conversation_input: List[Dict[str, Any]],
        user_id: str | None,
        page: str | None,
        name: str | None,
        email: str | None,
        message: str | None,
        mode: str,
        exam_context: str,
        exam_id: str | None,
        category: str,
        requires_visuals: bool,
        requires_web_search: bool,  
        arena_id: str | None,
        clean_pdfs: List[str],
        actual_conversation_id: str
    ) -> Tuple[str, Dict | None]:
        
        logger.info(f"ChatService Debug -> ExamID: {exam_id}, Page: {page}")

        # 1. Setup Resources
        selected_vector_stores = get_stores_for_page(page, exam_id=exam_id)
        
        # ROUTER-DRIVEN WEB SEARCH: We completely bypass the old context check
        web_search_config = {"scope": "open_web", "search_enabled": True} if requires_web_search else None
        is_web_search_active = requires_web_search

        # EXCLUSIVE TOOL GATING: Prevent tool conflict by removing vector stores if web search is active
        if is_web_search_active:
            selected_vector_stores = None
            logger.info("Web search flag active: File Search tool disabled to force Open Web execution.")

        runtime_signals = build_runtime_context(
            page=page, user_id=user_id, name=name, email=email, requires_visuals=requires_visuals
        )
        system_prompt = ""

        # 2. Handle Arenas Context
        if arena_id:
            try:
                arena_context = arena_service.get_arena_context(user_id, arena_id)
                if arena_context:
                    arena_title = arena_context.get('Title', 'Custom Arena')
                    arena_instructions = arena_context.get('SystemInstructions', '')
                    
                    arena_vector_store = arena_context.get('VectorStoreId')
                    # Respect tool gating for arena vector stores too
                    if arena_vector_store and not is_web_search_active:
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

                        injection = f"\n\n## Identity: {arena_title}\n{arena_instructions}"
                        system_prompt = base_tech_prompt + injection
            except Exception as e:
                logger.error(f"Failed to load arena context: {e}")

        # 3. Standard System Prompt Fallback
        if not system_prompt:
            system_prompt = build_system_instructions(
                extras=runtime_signals, 
                exam_context=exam_context, 
                requires_visuals=requires_visuals, 
                web_search_active=is_web_search_active, 
                intent="chat",
                category=category
            )

        # Look up explicit container ID to prevent duplicate billing
        active_container_id = None
        if requires_visuals or (clean_pdfs and len(clean_pdfs) > 0):
            try:
                active_container_id = ContainerUsageService().get_active_container_for_session(actual_conversation_id)
                if active_container_id:
                    logger.info(f"Reusing existing container ID: {active_container_id} for session {actual_conversation_id}")
            except Exception as e:
                logger.error(f"Failed to fetch active container: {e}")

        # 4. Call AI (Parallel Execution for Visuals)
        try:
            if requires_visuals:
                # Phase 1: Micro-latency Blueprint Generation
                blueprint_instruction = (
                    "You are the analytical engine. Based on the user's request, "
                    "generate a strict analytical blueprint for a mathematical or data plot. "
                )
                
                blueprint, blueprint_usage = generate_plot_blueprint(
                    conversation_input=conversation_input,
                    mode=mode,
                    system_instruction=blueprint_instruction
                )

                # Phase 1.5: Short-circuit validation
                is_valid_plot = blueprint.chart_type and "none" not in blueprint.chart_type.lower()

                if is_valid_plot:
                    text_prompt = system_prompt + (
                        f"\n\n[SYSTEM NOTE: A visual plot is simultaneously being generated with the following blueprint:\n"
                        f"Concept: {blueprint.analytical_concept}\n"
                        f"Type: {blueprint.chart_type}\n"
                        f"Ensure your conversational text explanation naturally aligns with this upcoming visualization. "
                        f"CRITICAL: Do NOT write any Python code, do NOT use Matplotlib, and do NOT output code blocks. "
                        f"Your only job is to explain the concept.]"
                    )
                else:
                    text_prompt = system_prompt

                # Phase 2: Parallel Execution of Text and Conditionally Visual Code
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    
                    future_text = executor.submit(
                        send_message_to_assistant,
                        conversation_input=conversation_input, 
                        user_id=user_id, 
                        page=page, 
                        name=(name or None), 
                        email=email,
                        mode=mode, 
                        system_instruction=text_prompt, 
                        vector_store_ids=selected_vector_stores, 
                        requires_visuals=False, 
                        web_search_config=web_search_config, 
                        user_location=None,
                        pdf_urls=clean_pdfs,
                        active_container_id=active_container_id,
                        conversation_id=actual_conversation_id
                    )

                    future_plot = None
                    if is_valid_plot:
                        future_plot = executor.submit(
                            execute_plot_generation,
                            blueprint=blueprint, 
                            mode=mode, 
                            active_container_id=active_container_id
                        )

                    response_tuple = future_text.result()
                    
                    plot_urls = []
                    plot_usage = {}
                    container_id = response_tuple[4] if len(response_tuple) > 4 else None

                    if future_plot:
                        plot_urls, plot_container_id, plot_usage = future_plot.result()
                        if plot_container_id:
                            container_id = plot_container_id

                    final_reply_text = response_tuple[0]
                    generated_assets = plot_urls
                    sources_data = response_tuple[2] if len(response_tuple) > 2 else []
                    
                    text_usage = response_tuple[3] if len(response_tuple) > 3 else {}
                    usage_data = {}
                    for key in ["input_tokens", "output_tokens", "total_tokens", "reasoning_tokens", "cached_tokens"]:
                        usage_data[key] = (
                            text_usage.get(key, 0) + 
                            blueprint_usage.get(key, 0) + 
                            plot_usage.get(key, 0)
                        )

            else:
                # Standard linear chat execution (No visuals required)
                response_tuple = send_message_to_assistant(
                    conversation_input=conversation_input, 
                    user_id=user_id, 
                    page=page, 
                    name=(name or None), 
                    email=email,
                    mode=mode, 
                    system_instruction=system_prompt, 
                    vector_store_ids=selected_vector_stores, 
                    requires_visuals=requires_visuals,
                    web_search_config=web_search_config, 
                    pdf_urls=clean_pdfs,
                    active_container_id=active_container_id,
                    conversation_id=actual_conversation_id  
                )
                
                final_reply_text = response_tuple[0]
                generated_assets = response_tuple[1]
                sources_data = response_tuple[2] if len(response_tuple) > 2 else []
                usage_data = response_tuple[3] if len(response_tuple) > 3 else {}
                container_id = response_tuple[4] if len(response_tuple) > 4 else None

            cls._log_usage(usage_data, user_id, actual_conversation_id, mode)
            cls._log_container(user_id, actual_conversation_id, container_id)

        except Exception as e:
            logger.error(f"OpenAI Chat API failed: {e}")
            raise RuntimeError(f"OpenAI Chat API failed: {e}")

        # 5. Format Metadata Payload
        meta_payload = {}  
        if generated_assets and requires_visuals:
            meta_payload["type"] = "rich_chat"
            meta_payload["assets"] = [{"type": "image", "url": url, "alt": "Generated Visualization"} for url in generated_assets]
        
        if sources_data:
            meta_payload["sources"] = sources_data
            
        if not meta_payload: 
            meta_payload = None

        return final_reply_text, meta_payload