# src/services/semantic_router.py
import logging
import json
from src.config.settings import settings, get_openai_client
from src.config.router_instructions import ROUTER_SYSTEM_INSTRUCTIONS 

logger = logging.getLogger(__name__)

class SemanticRouter:
    """
    Determines the intent/category of a user message and generates dynamic
    visual feedback phrases.
    """
    
    def __init__(self):
        self.client = get_openai_client()
        self.valid_categories = [
            "biologia", "quimica", "fisica", "matematicas", 
            "sociales", "lectura_critica", "analisis_imagen", "ingles",
            "general", "identity_protection"  #  SECURITY: Added identity_protection
        ]

    def determine_category(self, text: str) -> dict:
        if not text:
            return {
                "category": "general", 
                "intent": "chat",
                "requires_visuals": False,
                "num_questions": 5, # NEW: Default fallback
                "loading_phrases": ["Procesando...", "Esperando datos..."], 
                "source": "fallback"
            }
            
        try:
            result = self._classify_with_llm(text)
            return {
                "category": result.get("category", "general"),
                "intent": result.get("intent", "chat"),
                "requires_visuals": result.get("requires_visuals", False),
                "num_questions": result.get("num_questions", 5), # NEW: Pass the extracted number
                "loading_phrases": result.get("loading_phrases", ["Analizando...", "Pensando..."]),
                "source": "ai"
            }
        except Exception as e:
            logger.warning(f"Router: LLM classification failed: {e}")
            return {
                "category": "general", 
                "intent": "chat",
                "requires_visuals": False,
                "num_questions": 5, # NEW: Error fallback
                "loading_phrases": ["Analizando solicitud...", "Procesando información..."],
                "source": "error_fallback"
            }

    def _classify_with_llm(self, text: str) -> dict:
        router_model = settings.OPENAI_ROUTER_MODEL.lower()
        
        system_prompt = (
            f"{ROUTER_SYSTEM_INSTRUCTIONS}\n\n"
            f"User Input to Classify: \"{text}\""
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        is_reasoning_model = (
            router_model.startswith("o") and not router_model.startswith("gpt") 
            or "reasoning" in router_model
        )
        
        request_kwargs = {
            "model": router_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }

        if is_reasoning_model:
            # 🟢 Use Reasoning Effort
            request_kwargs["max_completion_tokens"] = 100 
            if settings.OPENAI_ROUTER_EFFORT:
                request_kwargs["reasoning_effort"] = settings.OPENAI_ROUTER_EFFORT
        else:
            # 🟢 Use Temperature/Top_P
            request_kwargs["max_tokens"] = 100 
            request_kwargs["temperature"] = settings.OPENAI_ROUTER_TEMP
            request_kwargs["top_p"] = settings.OPENAI_ROUTER_TOP_P

        try:
            response = self.client.chat.completions.create(**request_kwargs)
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            # Sanitize Category
            category = data.get("category", "general").lower()
            if category not in self.valid_categories: category = "general"

            # Sanitize Intent
            intent = data.get("intent", "chat").lower()
            if intent not in ["quiz", "chat"]: intent = "chat"

            # Extract Visual Intent
            requires_visuals = data.get("requires_visuals", False)
            if not isinstance(requires_visuals, bool):
                requires_visuals = False

            # NEW: Extract and Sanitize num_questions with Truncation Failsafe
            num_questions = data.get("num_questions", 5)
            if not isinstance(num_questions, int) or num_questions < 1:
                num_questions = 5
            elif num_questions > 30:
                num_questions = 30 # Safe Truncation to 30
                
            # Robust Extraction for phrases
            phrases = data.get("loading_phrases")
            if not phrases:
                phrases = data.get("status_messages") 
            if not phrases:
                phrases = data.get("phrases")
            if not phrases:
                phrases = data.get("loading_phounces") 

            # Final validation
            if not isinstance(phrases, list) or not phrases:
                phrases = ["Procesando...", "Analizando..."]

            logger.info(f"Router: AI classified as '{category}' (Intent: {intent}, Visuals: {requires_visuals}, Questions: {num_questions})")
            return {
                "category": category, 
                "intent": intent, 
                "requires_visuals": requires_visuals, 
                "num_questions": num_questions, # NEW: Add to return dict
                "loading_phrases": phrases
            }
            
        except Exception as e:
            logger.error(f"Router: Error calling OpenAI: {e}")
            raise e

# Singleton instance
semantic_router = SemanticRouter()