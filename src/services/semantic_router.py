# src/services/semantic_router.py
import logging
from typing import List, Literal
from pydantic import BaseModel, Field
from src.config.settings import settings, get_openai_client
from src.config.router_instructions import ROUTER_SYSTEM_INSTRUCTIONS 
from src.services.token_usage_service import TokenUsageService

logger = logging.getLogger(__name__)

# 🟢 NEW: Strict Pydantic Schema for 100% Reliable Routing
class RouterResponse(BaseModel):
    category: str = Field(description="The academic category or subject of the query (e.g., biologia, matematicas, admisiones, general).")
    intent: Literal["chat", "quiz", "creative_image", "admission_stats"] = Field(description="The primary intent of the user.")
    requires_visuals: bool = Field(description="True if the user is asking for graphs, charts, or visual analysis.")
    num_questions: int = Field(description="The number of questions requested if the intent is 'quiz'. 0 otherwise.")
    loading_phrases: List[str] = Field(description="2 to 3 engaging loading phrases in Spanish relevant to the query.")

class SemanticRouter:
    """
    Determines the intent/category of a user message and generates dynamic
    visual feedback phrases using the new Responses API and Structured Outputs.
    """
    
    def __init__(self):
        self.client = get_openai_client()
        self.valid_categories = [
            "biologia", "quimica", "fisica", "matematicas", 
            "sociales", "lectura_critica", "analisis_imagen", "ingles",
            "general", "identity_protection", 
            "admisiones"
        ]

    def determine_category(self, text: str) -> dict:
        if not text:
            return {
                "category": "general", 
                "intent": "chat",
                "requires_visuals": False,
                "num_questions": 0,
                "loading_phrases": ["Procesando...", "Esperando datos..."], 
                "source": "fallback"
            }
            
        try:
            result = self._classify_with_llm(text)
            return {
                "category": result.get("category", "general"),
                "intent": result.get("intent", "chat"),
                "requires_visuals": result.get("requires_visuals", False),
                "num_questions": result.get("num_questions", 0),
                "loading_phrases": result.get("loading_phrases", ["Analizando...", "Pensando..."]),
                "source": "ai"
            }
        except Exception as e:
            logger.warning(f"Router: LLM classification failed: {e}")
            return {
                "category": "general", 
                "intent": "chat",
                "requires_visuals": False,
                "num_questions": 0,
                "loading_phrases": ["Analizando solicitud...", "Procesando información..."],
                "source": "error_fallback"
            }

    def _classify_with_llm(self, text: str) -> dict:
        router_model = settings.OPENAI_ROUTER_MODEL.lower()
        
        # 🟢 CHANGED: payload shape from 'messages' to 'input'
        api_input = [
            {"role": "system", "content": ROUTER_SYSTEM_INSTRUCTIONS.strip()},
            {"role": "user", "content": text}
        ]
        
        is_reasoning_model = (
            router_model.startswith("o") and not router_model.startswith("gpt") 
            or "reasoning" in router_model
        )
        
        request_kwargs = {
            "model": router_model,
            "input": api_input,
            "text_format": RouterResponse, # 🟢 CHANGED: response_format to text_format using Pydantic
        }

        # Handle Responses API parameters
        if is_reasoning_model:
            if settings.OPENAI_ROUTER_EFFORT:
                request_kwargs["reasoning"] = {"effort": settings.OPENAI_ROUTER_EFFORT}
        else:
            request_kwargs["temperature"] = settings.OPENAI_ROUTER_TEMP
            request_kwargs["top_p"] = settings.OPENAI_ROUTER_TOP_P

        try:
            # 🟢 CHANGED: completions.create to responses.parse
            response = self.client.responses.parse(**request_kwargs)
            
            # Extract Structured Output securely
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

            # 🟢 NEW: Capture and log Router Token Usage
            usage = getattr(response, "usage", None)
            if usage:
                try:
                    if isinstance(usage, dict):
                        input_val = usage.get("input_tokens", 0)
                        output_val = usage.get("output_tokens", 0)
                        total_val = usage.get("total_tokens", 0)
                        reasoning_val = usage.get("output_tokens_details", {}).get("reasoning_tokens", 0)
                        cached_val = usage.get("input_tokens_details", {}).get("cached_tokens", 0)
                    else:
                        input_val = getattr(usage, "input_tokens", 0)
                        output_val = getattr(usage, "output_tokens", 0)
                        total_val = getattr(usage, "total_tokens", 0)
                        out_details = getattr(usage, "output_tokens_details", None)
                        reasoning_val = getattr(out_details, "reasoning_tokens", 0) if out_details else 0
                        in_details = getattr(usage, "input_tokens_details", None)
                        cached_val = getattr(in_details, "cached_tokens", 0) if in_details else 0

                    TokenUsageService().log_token_usage(
                        user_id="system_router",
                        session_id="intent_resolution",
                        model=router_model,
                        input_tokens=input_val,
                        output_tokens=output_val,
                        total_tokens=total_val,
                        reasoning_tokens=reasoning_val,
                        cached_tokens=cached_val
                    )
                except Exception as e:
                    logger.error(f"Failed to log router tokens: {e}")

            # Convert Pydantic object to dictionary
            data = parsed_data.model_dump() if hasattr(parsed_data, "model_dump") else parsed_data.dict()
            
            # Final Sanitize (Guarantees backward compatibility)
            category = data.get("category", "general").lower()
            if category not in self.valid_categories: category = "general"

            intent = data.get("intent", "chat").lower().strip()
            if intent not in ["quiz", "chat", "creative_image", "admission_stats"]: 
                intent = "chat"

            requires_visuals = data.get("requires_visuals", False)

            if intent != "quiz":
                num_questions = 0
            else:
                num_questions = data.get("num_questions", 5)
                if num_questions < 1: num_questions = 5
                elif num_questions > 30: num_questions = 30
                
            phrases = data.get("loading_phrases", [])
            if not phrases:
                phrases = ["Procesando...", "Analizando..."]

            logger.info(f"Router: AI classified as '{category}' (Intent: {intent}, Visuals: {requires_visuals}, Questions: {num_questions})")
            return {
                "category": category, 
                "intent": intent, 
                "requires_visuals": requires_visuals, 
                "num_questions": num_questions,
                "loading_phrases": phrases
            }
            
        except Exception as e:
            logger.error(f"Router: Error calling OpenAI Responses API: {e}")
            raise e

# Singleton instance
semantic_router = SemanticRouter()