# src/services/mindmap_service.py
import logging
from src.config.settings import settings, get_openai_client
from src.schemas.mindmap_schemas import MindMapPayload
from src.config.mindmap_instructions import build_mindmap_instructions
from src.services.token_usage_service import TokenUsageService

# 🟢 NEW: Import the dynamic model config
from src.config.model_config import get_model_config

logger = logging.getLogger(__name__)

class MindMapService:
    def __init__(self):
        self.client = get_openai_client()

    # 🟢 FIX: Added 'mode' parameter to accept alpha/omega
    def generate_mindmap(self, topic: str, user_id: str, conversation_id: str, exam_context: str = "GENERAL", mode: str = "omega") -> dict:
        try:
            # 🟢 FIX: Get the exact model engine for the active tier
            cfg = get_model_config(mode)
            target_model = cfg.model
            
            # 1. Get the pedagogical instructions
            system_prompt = build_mindmap_instructions(exam_context)
            
            logger.info(f"Generating mind map for topic: '{topic}' in context: '{exam_context}' using engine: {target_model}")
            
            # 2. Call OpenAI with Structured Outputs
            response = self.client.chat.completions.parse(
                model=target_model, # 🟢 FIX: Using the dynamic model!
                messages=[
                    {"role": "system", "content": system_prompt.strip()},
                    {"role": "user", "content": f"Create a highly structured academic mind map for the following topic: {topic}"}
                ],
                response_format=MindMapPayload,
                temperature=0.3 # Low temperature for logical, structured generation
            )
            
            message = response.choices[0].message
            
            # 3. Handle Refusals (Safety check)
            if getattr(message, 'refusal', None):
                logger.warning(f"Mind Map generation refused: {message.refusal}")
                raise ValueError(f"El asistente no puede procesar este tema: {message.refusal}")
            
            if not getattr(message, 'parsed', None):
                raise ValueError("Failed to parse structured output from OpenAI.")
                
            parsed_data = message.parsed
            
            # 4. Log Token Usage
            usage = getattr(response, "usage", None)
            if usage:
                try:
                    TokenUsageService().log_token_usage(
                        user_id=user_id, 
                        conversation_id=conversation_id, 
                        source="mindmap_generator",                 
                        tier=mode,         # 🟢 FIX: Log the actual tier
                        engine=target_model, # 🟢 FIX: Log the actual model engine
                        input_tokens=getattr(usage, "prompt_tokens", 0), 
                        output_tokens=getattr(usage, "completion_tokens", 0), 
                        total_tokens=getattr(usage, "total_tokens", 0)
                    )
                except Exception as token_err:
                    logger.error(f"Failed to log mind map tokens: {token_err}")

            # 5. Export dictionary using alias (CRITICAL: converts 'source' back to 'from')
            payload_dict = parsed_data.model_dump(by_alias=True)
            
            return payload_dict
            
        except Exception as e:
            logger.error(f"Error generating mind map: {e}")
            raise e

# Singleton instance
mindmap_service = MindMapService()