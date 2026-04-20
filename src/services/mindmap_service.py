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

    def generate_mindmap(self, topic: str, user_id: str, conversation_id: str, exam_context: str = "GENERAL", mode: str = "omega") -> dict:
        try:
            cfg = get_model_config(mode)
            target_model = cfg.model
            
            # 1. Get the pedagogical instructions
            system_prompt = build_mindmap_instructions(exam_context)
            
            logger.info(f"Generating mind map for topic: '{topic}' in context: '{exam_context}' using engine: {target_model}")
            
            api_input = [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": f"Create a highly structured academic mind map for the following topic: {topic}"}
            ]

            # 2. Determine if it's a reasoning model to handle kwargs safely
            is_reasoning_model = (
                target_model.startswith("o") and not target_model.startswith("gpt") 
                or "reasoning" in target_model
            )

            request_kwargs = {
                "model": target_model,
                "input": api_input,
                "text_format": MindMapPayload, # Responses API uses text_format instead of response_format
            }

            if is_reasoning_model:
                if cfg.reasoning_effort:
                    request_kwargs["reasoning"] = {"effort": cfg.reasoning_effort}
            else:
                request_kwargs["temperature"] = cfg.temperature if cfg.temperature is not None else 0.3
                if cfg.top_p is not None:
                    request_kwargs["top_p"] = cfg.top_p

            # 3. Call OpenAI Responses API with Structured Outputs
            response = self.client.responses.parse(**request_kwargs)
            
            parsed_data = None
            if hasattr(response, 'output_parsed') and response.output_parsed:
                parsed_data = response.output_parsed
            else:
                for out in getattr(response, 'output', []):
                    if getattr(out, "type", "") == "message":
                        for item in getattr(out, "content", []):
                            if getattr(item, "parsed", None):
                                parsed_data = item.parsed
                                break

            if not parsed_data:
                raise ValueError("Failed to parse structured output from Responses API.")
            
            # 4. Log Token Usage (Using Responses API structure)
            usage = getattr(response, "usage", None)
            if usage:
                try:
                    if isinstance(usage, dict):
                        input_val = usage.get("input_tokens", usage.get("prompt_tokens", 0))
                        output_val = usage.get("output_tokens", usage.get("completion_tokens", 0))
                        total_val = usage.get("total_tokens", 0)
                    else:
                        input_val = getattr(usage, "input_tokens", getattr(usage, "prompt_tokens", 0))
                        output_val = getattr(usage, "output_tokens", getattr(usage, "completion_tokens", 0))
                        total_val = getattr(usage, "total_tokens", 0)

                    TokenUsageService().log_token_usage(
                        user_id=user_id, 
                        conversation_id=conversation_id, 
                        source="mindmap_generator",                 
                        tier=mode,         
                        engine=target_model, 
                        input_tokens=input_val, 
                        output_tokens=output_val, 
                        total_tokens=total_val
                    )
                except Exception as token_err:
                    logger.error(f"Failed to log mind map tokens: {token_err}")

            # 5. Export dictionary using alias (CRITICAL: converts 'source' back to 'from')
            payload_dict = parsed_data.model_dump(by_alias=True) if hasattr(parsed_data, "model_dump") else parsed_data.dict(by_alias=True)
            
            return payload_dict
            
        except Exception as e:
            logger.error(f"Error generating mind map: {e}")
            raise e

# Singleton instance
mindmap_service = MindMapService()