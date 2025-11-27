# src/services/semantic_router.py
import logging
from src.config.settings import settings, get_openai_client

logger = logging.getLogger(__name__)

class SemanticRouter:
    """
    Determines the intent/category of a user message to provide immediate
    visual feedback. Uses a Hybrid approach:
    1. Fast Regex/Keyword check (Zero Latency)
    2. LLM Classification (Low Latency Fallback)
    """
    
    def __init__(self):
        # We use the shared client helper
        self.client = get_openai_client()
        
        # 1. Define categories and their keywords for the ZERO LATENCY check
        # These are roots/stems to catch variations (e.g., "biolog" catches "biology", "biológico")
        self.keyword_map = {
            "biologia": [
                # Spanish
                "celula", "célula", "biolog", "genétic", "adn", "ecosistema", 
                "plant", "animal", "mitosis", "meiosis", "protein", "enzim", 
                "bacteria", "virus", "inmune", "nervioso", "vida", "organismo",
                "mitocondria", 
                # English
                "cell", "dna", "mitochondria", "life", "organism"
            ],
            "matematicas": [
                # Spanish
                "calcul", "deriv", "integr", "ecuacion", "física", "química", 
                "molar", "átomo", "numero", "algebra", "trigonometr", "velocidad", 
                "fuerza", "energía", "sumar", "restar", "multiplicar", "dividir", 
                "logaritmo", "exponente", "soluci",
                # New additions for robustness:
                "suma", "resta", "angul", 
                # English
                "math", "equation", "solve", "physics", "chemistry", "atom", "speed", "force",
                "angle"
            ],
            "historia": [
                # Spanish
                "historia", "guerra", "constitución", "siglo", "quién fue", 
                "colombia", "president", "revolución", "independencia", 
                "democracia", "derecho", "ciudadan", "imperio", "batalla", "gobierno",
                # English
                "history", "war", "century", "who was", "revolution", "government"
            ],
            "ingles": [
                # Spanish
                "traduc", "ingles", "significado", "resumen", "verbo", "gramatica", "ortografía",
                # English
                "english", "translate", "meaning", "essay", "verb", "grammar", "spelling"
            ]
        }
        
        # 2. Map categories to user-facing status messages (The Visual Feedback)
        self.status_messages = {
            "biologia": "Consultando base de datos biológica...",
            "matematicas": "Analizando lógica matemática...",
            "historia": "Consultando archivos históricos...",
            "ingles": "Procesando análisis lingüístico...",
            "general": "Analizando tu pregunta..."
        }

    def determine_status(self, text: str) -> str:
        """
        Main entry point. Returns the status text to show the user.
        """
        if not text:
            return "Procesando..."
            
        # --- STEP 1: FAST CHECK (Regex/Keywords) ---
        # Latency: ~0.01 seconds
        text_lower = text.lower()
        for category, keywords in self.keyword_map.items():
            if any(k in text_lower for k in keywords):
                logger.info(f"Router: Keyword match found for '{category}'")
                return self.status_messages.get(category)
                
        # --- STEP 2: SMART CHECK (LLM Fallback) ---
        # Latency: ~0.5 seconds (depends on model)
        # Only runs if no keywords matched (e.g., user asked about "dolphins")
        try:
            return self._classify_with_llm(text)
        except Exception as e:
            logger.warning(f"Router: LLM classification failed: {e}")
            return self.status_messages["general"]

    def _classify_with_llm(self, text: str) -> str:
        """
        Asks a small, fast model to classify the text.
        Uses the model defined in settings (OPENAI_ROUTER_MODEL).
        """
        # Define the valid categories for the AI
        categories = ["biologia", "matematicas", "historia", "ingles", "general"]
        
        # Use the model configured in settings (defaults to gpt-4o-mini)
        router_model = settings.OPENAI_ROUTER_MODEL
        
        try:
            response = self.client.chat.completions.create(
                model=router_model, 
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            f"Classify the user input into one of these categories: {', '.join(categories)}. "
                            "Return ONLY the category name. If unsure or off-topic, return 'general'."
                        )
                    },
                    {"role": "user", "content": text}
                ],
                max_tokens=10, # We only need one word
                temperature=0.0 # Deterministic results
            )
            
            category = response.choices[0].message.content.strip().lower()
            logger.info(f"Router: AI classified as '{category}' using {router_model}")
            
            # Return the mapped message, or default if the AI hallucinated a new category
            return self.status_messages.get(category, self.status_messages["general"])
            
        except Exception as e:
            logger.error(f"Router: Error calling OpenAI: {e}")
            raise e

# Singleton instance for easy import
semantic_router = SemanticRouter()