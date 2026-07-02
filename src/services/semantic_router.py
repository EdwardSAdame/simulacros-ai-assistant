# src/services/semantic_router.py
import logging
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from src.config.settings import settings, get_openai_client
from src.config.router_instructions import build_router_instructions 
from src.services.token_usage_service import TokenUsageService

logger = logging.getLogger(__name__)

class RouterResponse(BaseModel):
    category: str = Field(description="The academic category or subject of the query.")
    intent: Literal["chat", "quiz", "creative_image", "admission_stats", "mentalMap", "flashcards"] = Field(description="The primary intent of the user. Use 'mentalMap' if the user asks for a mind map, conceptual map, or structural diagram. Use 'flashcards' for studying, memorizing, or reviewing facts.")
    requires_visuals: bool = Field(description="True if the user is asking for graphs, charts, or visual analysis.")
    num_questions: int = Field(description="The number of questions requested if the intent is 'quiz', or the number of cards if the intent is 'flashcards'. Return 0 if the user does not specify a number.")
    loading_phrases: List[str] = Field(description="2 to 3 engaging loading phrases in Spanish relevant to the query.")

class SemanticRouter:
    """
    Determines the intent/category of a user message dynamically based on Exam Context.
    """
    
    def __init__(self):
        self.client = get_openai_client()
        
        # Unified validation list containing all possible dynamic categories
        self.valid_categories = [
            "matematicas", "ciencias_naturales", "analisis_textual", 
            "ciencias_sociales", "analisis_imagen", "lectura_critica", 
            "sociales_ciudadanas", "ingles", "admisiones", 
            "identity_protection", "general"
        ]
        
        self.visual_categories = [
            "matematicas", "ciencias_naturales", "analisis_imagen", "general"
        ]

    def determine_category(self, text: str, user_id: str = "system_router", conversation_id: str = "intent_resolution", exam_context: str = "GENERAL", history: Optional[List[dict]] = None, current_activity: str = "chat") -> dict:
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
            # Pass current_activity to the LLM classifier
            result = self._classify_with_llm(text, user_id, conversation_id, exam_context, history, current_activity)
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

    def _classify_with_llm(self, text: str, user_id: str, conversation_id: str, exam_context: str, history: Optional[List[dict]] = None, current_activity: str = "chat") -> dict:
        router_model = settings.OPENAI_ROUTER_MODEL.lower()
        
        # Build instructions dynamically based on context AND sticky state
        system_instruction = build_router_instructions(exam_context, current_activity)
        
        api_input = [
            {"role": "system", "content": system_instruction.strip()}
        ]

        # Inject brief conversation history for context resolution
        if history:
            # Only take the last 6 messages to avoid bloating token usage on the router
            recent_history = history[-6:]
            for msg in recent_history:
                role = msg.get("role")
                content = msg.get("content")
                if role in ["user", "assistant"] and content:
                    # Truncate assistant responses to save tokens, we only need the gist
                    content_str = str(content)
                    if role == "assistant" and len(content_str) > 300:
                        content_str = content_str[:300] + "... [truncated]"
                    api_input.append({"role": role, "content": content_str})

        api_input.append({"role": "user", "content": text})
        
        is_reasoning_model = (
            router_model.startswith("o") and not router_model.startswith("gpt") 
            or "reasoning" in router_model
        )
        
        request_kwargs = {
            "model": router_model,
            "input": api_input,
            "text_format": RouterResponse, 
        }

        if is_reasoning_model:
            if settings.OPENAI_ROUTER_EFFORT:
                request_kwargs["reasoning"] = {"effort": settings.OPENAI_ROUTER_EFFORT}
        else:
            request_kwargs["temperature"] = settings.OPENAI_ROUTER_TEMP
            request_kwargs["top_p"] = settings.OPENAI_ROUTER_TOP_P

        try:
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

            # (Token Tracking Logic)
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
                        user_id=user_id, 
                        conversation_id=conversation_id, 
                        source="router",                 
                        tier="router",        
                        engine=router_model,  
                        input_tokens=input_val, 
                        output_tokens=output_val, 
                        total_tokens=total_val,
                        reasoning_tokens=reasoning_val, 
                        cached_tokens=cached_val
                    )
                except Exception as e:
                    logger.error(f"Failed to log router tokens: {e}")

            data = parsed_data.model_dump() if hasattr(parsed_data, "model_dump") else parsed_data.dict()
            
            category = data.get("category", "general").lower()
            if category not in self.valid_categories: category = "general"

            raw_intent = data.get("intent", "chat").strip()
            intent_lower = raw_intent.lower()
            
            if intent_lower in ["mentalmap", "mental_map"]:
                intent = "mentalMap"
            elif intent_lower in ["quiz", "chat", "creative_image", "admission_stats", "flashcards"]: 
                intent = intent_lower
            else:
                intent = "chat"

            requires_visuals = data.get("requires_visuals", False)

            if intent == "quiz" and category in self.visual_categories:
                requires_visuals = True
                logger.info(f"Router Override: Enforcing requires_visuals=True for {category} quiz to apply visual doctrine styling.")

            # ----- CLEAN ARCHITECTURE UPDATE -----
            # The router no longer decides limits or randomizes numbers.
            # It just extracts the explicit user intent and passes it down.
            if intent not in ["quiz", "flashcards"]:
                num_questions = 0
            else:
                num_questions = data.get("num_questions", 0)
            # -------------------------------------
                
            phrases = data.get("loading_phrases", [])
            if not phrases:
                phrases = ["Procesando...", "Analizando..."]

            logger.info(f"Router: AI classified as '{category}' with intent '{intent}' in context '{exam_context}' and active state '{current_activity}'")
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