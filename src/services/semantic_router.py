# src/services/semantic_router.py
import logging
import json
from src.config.settings import settings, get_openai_client

logger = logging.getLogger(__name__)

class SemanticRouter:
    """
    Determines the intent/category of a user message and generates dynamic
    visual feedback phrases.
    
    Updated: Relies 100% on AI (LLM) for classification. No Regex.
    """
    
    def __init__(self):
        self.client = get_openai_client()
        # Define the valid categories for the AI to choose from
        self.valid_categories = [
            "biologia", "quimica", "fisica", "matematicas", 
            "sociales", "lectura_critica", "analisis_imagen", "ingles",
            "general"
        ]

    def determine_category(self, text: str) -> dict:
        """
        Main entry point. Now purely uses AI to classify.
        """
        if not text:
            return {
                "category": "general", 
                "loading_phrases": ["Procesando...", "Esperando datos..."], 
                "source": "fallback"
            }
            
        try:
            result = self._classify_with_llm(text)
            return {
                "category": result.get("category", "general"),
                # Ensure we pull the corrected key, or fall back safely
                "loading_phrases": result.get("loading_phrases", ["Analizando...", "Pensando..."]),
                "source": "ai"
            }
        except Exception as e:
            logger.error(f"Router: CRITICAL LLM classification failed: {e}")
            return {
                "category": "general", 
                "loading_phrases": ["Analizando solicitud...", "Procesando información..."],
                "source": "error_fallback"
            }

    def _classify_with_llm(self, text: str) -> dict:
        """
        Asks the AI to classify AND generate creative status messages.
        Includes dynamic handling for model-specific parameters.
        """
        router_model = settings.OPENAI_ROUTER_MODEL.lower() # Ensure model is lowercase for checks
        categories_str = ", ".join(self.valid_categories) 
        
        system_prompt = (
            f"You are the brain of an advanced AI tutor named Roma. "
            f"1. Classify the input into one of: {categories_str}. "
            f"2. Generate 3 short, authoritative, 'tech-noir' style status messages (max 4 words each) "
            f"that describe the thinking process for this specific query. "
            f"Use the same language as the user's input (Spanish or English). "
            f"Example for 'nostalgia': ['Analyzing emotional depth...', 'Decoding human memory...', 'Synthesizing context...']. "
            f"Return JSON: {{ 'category': '...', 'loading_phrases': ['str', 'str', 'str'] }}."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        # 🔹 NEW/UPDATED: Check for all Reasoning Models
        # This includes any model starting with 'o' (o1, o3, o4-mini, etc.), plus 'nano' and 'reasoning'.
        is_reasoning_model = (
            router_model.startswith("o") or 
            "nano" in router_model or 
            "reasoning" in router_model
        )
        
        # 🔹 DYNAMIC ARGUMENT BUILDER 
        request_kwargs = {
            "model": router_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }

        # 🔹 CONDITIONAL PARAMETER SWITCH
        if is_reasoning_model:
            # Reasoning models (like o1) use 'max_completion_tokens'
            request_kwargs["max_completion_tokens"] = 100 
            # Suppress temperature/top_p by omission, as is best practice for these models
            logger.info(f"Router TRACER: Model '{router_model}' is reasoning; using max_completion_tokens.")

        else:
            # Standard models (gpt-4o, gpt-4.1-mini) use 'max_tokens' 
            # and accept configurable temperature/top_p.
            request_kwargs["max_tokens"] = 100 
            request_kwargs["temperature"] = settings.OPENAI_ROUTER_TEMP
            request_kwargs["top_p"] = settings.OPENAI_ROUTER_TOP_P
            logger.info(f"Router TRACER: Calling {router_model} with Temp={settings.OPENAI_ROUTER_TEMP}")


        try:
            # 🔹 TRACER: Log the model being used
            temp_value = request_kwargs.get("temperature", "N/A (suppressed)")
            logger.info(f"Router TRACER: Calling {router_model} with Temp={temp_value}")
            
            response = self.client.chat.completions.create(**request_kwargs)
            
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            # 🔹 FIX 2: Handle known model hallucination/typo in JSON key 
            if "loading_phounces" in data and "loading_phrases" not in data:
                 data["loading_phrases"] = data.pop("loading_phounces") 
                 logger.warning("Router: Corrected model typo: 'loading_phounces' to 'loading_phrases'")

            category = data.get("category", "general").lower()
            if category not in self.valid_categories:
                category = "general"
                
            phrases = data.get("loading_phrases", [])
            if not isinstance(phrases, list) or not phrases:
                phrases = ["Procesando...", "Analizando..."]

            logger.info(f"Router: AI classified as '{category}' with phrases {phrases}")
            return {"category": category, "loading_phrases": phrases}
            
        except Exception as e:
            # Log the full error and re-raise it for the top-level error handler
            logger.error(f"Router: Error calling OpenAI: {e}")
            raise e

# Singleton instance
semantic_router = SemanticRouter()