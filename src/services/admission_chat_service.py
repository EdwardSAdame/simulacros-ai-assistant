# src/services/admission_chat_service.py
import logging
from typing import Dict, Any, Tuple, List

from src.services.context_builder import build_runtime_context
from src.config.system_instructions import build_system_instructions
from src.assistant.assistant_client import stream_chat_response
from src.services.token_usage_service import TokenUsageService

logger = logging.getLogger(__name__)

class AdmissionChatService:
    """
    Handles AI chat interactions specifically focused on querying 
    and analyzing university admission statistics.
    """

    @staticmethod
    def _log_usage(usage_data: dict, current_user: str | None, session: str, active_mode: str):
        """Helper to log token usage telemetry for admission queries."""
        if not usage_data or not current_user: 
            return
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
            logger.error(f"Failed to log token usage in AdmissionChatService: {e}")

    @classmethod
    def execute_admission_chat(
        cls,
        conversation_input: List[Dict[str, Any]],
        user_id: str | None,
        page: str | None,
        name: str | None,
        email: str | None,
        mode: str,
        exam_context: str,
        category: str,
        actual_conversation_id: str
    ) -> Tuple[str, Dict | None]:
        """
        Executes the admission stats AI query by building the required context,
        triggering the local tool, and parsing the stream.
        """
        logger.info(f"Routing to Admission Stats local tool for user {user_id}")
        
        final_reply_text = ""
        meta_payload = None

        try:
            # 1. Build context without visuals (Admission tool is text/data focused)
            runtime_signals = build_runtime_context(
                page=page, user_id=user_id, name=name, email=email, requires_visuals=False 
            )
            
            system_prompt = build_system_instructions(
                extras=runtime_signals, 
                exam_context=exam_context, 
                requires_visuals=False, 
                web_search_active=False, 
                intent="admission_stats",
                category=category
            )

            # 2. Trigger the stream with function calling allowed
            stream_gen = stream_chat_response(
                conversation_input=conversation_input, 
                user_id=user_id, 
                page=page, 
                name=name, 
                email=email, 
                mode=mode, 
                enable_image_generation=False,
                system_instruction=system_prompt
            )
            
            # 3. Parse the stream
            for event in stream_gen:
                if isinstance(event, dict) and event.get("type") == "usage_metrics":
                    cls._log_usage(event.get("data"), user_id, actual_conversation_id, mode)
                
                elif getattr(event, "type", "") == "response.output_text.delta":
                    final_reply_text += getattr(event, "delta", "")
                    
        except Exception as e:
            logger.error(f"Admission Stats Generation Error: {e}")
            final_reply_text = "**Error**: Hubo un problema consultando la base de datos de admisiones."
            meta_payload = None

        return final_reply_text, meta_payload