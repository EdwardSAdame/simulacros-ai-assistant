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
    Now detects INTENT (Quiz vs Chat).
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
            "intent": "quiz" | "chat",  # <--- NEW FIELD
            "loading_phrases": [str, str, str],
            "source": "ai" | "error_fallback"
        }
        """
        if not text:
            return {
                "category": "general", 
                "intent": "chat",
                "loading_phrases": ["Procesando...", "Esperando datos..."], 
                "source": "fallback"
            }
            
        # --- DIRECT LLM CALL (No Regex) ---
        try:
            result = self._classify_with_llm(text)
            return {
                "category": result.get("category", "general"),
                "intent": result.get("intent", "chat"), # <--- Pass intent through
                "loading_phrases": result.get("loading_phrases", ["Analizando...", "Pensando..."]),
                "source": "ai"
            }
        except Exception as e:
            logger.warning(f"Router: LLM classification failed: {e}")
            return {
                "category": "general", 
                "intent": "chat",
                "loading_phrases": ["Analizando solicitud...", "Procesando información..."],
                "source": "error_fallback"
            }

    def _classify_with_llm(self, text: str) -> dict:
        """
        Asks the AI to classify Category AND Intent, plus generate creative status messages.
        """
        router_model = settings.OPENAI_ROUTER_MODEL.lower()
        categories_str = ", ".join(self.valid_categories)
        
        # 🔹 UPDATED PROMPT: Stronger instructions for dynamic phrases
        system_prompt = (
            f"You are the brain of an advanced AI tutor named Roma. "
            f"1. Classify the input into one of: {categories_str}. "
            f"2. Determine the INTENT. Is the user explicitly asking to take a quiz, exam, test, or simulacrum? "
            f"   - If yes -> intent: 'quiz' "
            f"   - If they are just asking a question or chatting -> intent: 'chat' "
            f"3. Generate 3 short, authoritative, 'tech-noir' style status messages (max 4 words each). "
            f"   - **STRICT RULE**: The phrases must be 100 percent UNIQUE and specific to the detected category/topic. "
            f"   - **FORBIDDEN**: Do NOT use generic phrases"
            f"   - If the intent is 'quiz', the phrases should sound like you are constructing an exam"
            f"   - Use the same language as the user's input (Spanish or English). "
            f"Return JSON: {{ 'category': '...', 'intent': 'quiz' | 'chat', 'loading_phrases': ['str', 'str', 'str'] }}."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        is_reasoning_model = (
            router_model.startswith("o") or 
            "nano" in router_model or 
            "reasoning" in router_model
        )
        
        request_kwargs = {
            "model": router_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }

        if is_reasoning_model:
            request_kwargs["max_completion_tokens"] = 100 
            logger.info(f"Router TRACER: Model '{router_model}' is reasoning; using max_completion_tokens.")
        else:
            request_kwargs["max_tokens"] = 100 
            request_kwargs["temperature"] = settings.OPENAI_ROUTER_TEMP
            request_kwargs["top_p"] = settings.OPENAI_ROUTER_TOP_P
            logger.info(f"Router TRACER: Calling {router_model} with Temp={settings.OPENAI_ROUTER_TEMP}")

        try:
            response = self.client.chat.completions.create(**request_kwargs)
            
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            # Sanitize Category
            category = data.get("category", "general").lower()
            if category not in self.valid_categories:
                category = "general"

            # Sanitize Intent (Default to chat if missing)
            intent = data.get("intent", "chat").lower()
            if intent not in ["quiz", "chat"]:
                intent = "chat"
                
            # Sanitize Phrases
            phrases = data.get("loading_phrases", [])
            # Fix typo fallback
            if "loading_phounces" in data and not phrases:
                 phrases = data.pop("loading_phounces")

            if not isinstance(phrases, list) or not phrases:
                phrases = ["Procesando...", "Analizando..."]

            logger.info(f"Router: AI classified as '{category}' (Intent: {intent}) with phrases {phrases}")
            return {"category": category, "intent": intent, "loading_phrases": phrases}
            
        except Exception as e:
            logger.error(f"Router: Error calling OpenAI: {e}")
            raise e

# Singleton instance
semantic_router = SemanticRouter()