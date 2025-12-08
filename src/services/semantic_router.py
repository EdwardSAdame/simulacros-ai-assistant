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
        Returns:
        {
            "category": str,
            "loading_phrases": [str, str, str],
            "source": "ai" | "error_fallback"
        }
        """
        if not text:
            return {
                "category": "general", 
                "loading_phrases": ["Procesando...", "Esperando datos..."], 
                "source": "fallback"
            }
            
        # --- DIRECT LLM CALL (No Regex) ---
        try:
            result = self._classify_with_llm(text)
            return {
                "category": result.get("category", "general"),
                "loading_phrases": result.get("loading_phrases", ["Analizando...", "Pensando..."]),
                "source": "ai"
            }
        except Exception as e:
            logger.warning(f"Router: LLM classification failed: {e}")
            return {
                "category": "general", 
                "loading_phrases": ["Analizando solicitud...", "Procesando información..."],
                "source": "error_fallback"
            }

    def _classify_with_llm(self, text: str) -> dict:
        """
        Asks the AI to classify AND generate creative status messages.
        """
        router_model = settings.OPENAI_ROUTER_MODEL
        categories_str = ", ".join(self.valid_categories)
        
        # Prompt designed for creativity and awareness of the user's language
        system_prompt = (
            f"You are the brain of an advanced AI tutor named Roma. "
            f"1. Classify the input into one of: {categories_str}. "
            f"2. Generate 3 short, authoritative, 'tech-noir' style status messages (max 4 words each) "
            f"that describe the thinking process for this specific query. "
            f"Use the same language as the user's input (Spanish or English). "
            f"Example for 'nostalgia': ['Analyzing emotional depth...', 'Decoding human memory...', 'Synthesizing context...']. "
            f"Return JSON: {{ 'category': '...', 'loading_phrases': ['str', 'str', 'str'] }}."
        )

        try:
            response = self.client.chat.completions.create(
                model=router_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=100, 
                temperature=0.7, 
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            category = data.get("category", "general").lower()
            if category not in self.valid_categories:
                category = "general"
                
            phrases = data.get("loading_phrases", [])
            # Ensure we have a list of strings
            if not isinstance(phrases, list) or not phrases:
                phrases = ["Procesando...", "Analizando..."]

            logger.info(f"Router: AI classified as '{category}' with phrases {phrases}")
            return {"category": category, "loading_phrases": phrases}
            
        except Exception as e:
            logger.error(f"Router: Error calling OpenAI: {e}")
            raise e

# Singleton instance
semantic_router = SemanticRouter()