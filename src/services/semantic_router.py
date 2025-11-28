# src/services/semantic_router.py
import logging
from src.config.settings import settings, get_openai_client

logger = logging.getLogger(__name__)

class SemanticRouter:
    """
    Determines the intent/category of a user message.
    Returns a dict with 'category' and 'source' (regex/ai).
    """
    
    def __init__(self):
        self.client = get_openai_client()
        
        # 1. Define categories and their keywords
        # Spanish terms are prioritized.
        self.keyword_map = {
            "biologia": [
                "celula", "célula", "biolog", "genétic", "adn", "ecosistema", 
                "plant", "animal", "mitosis", "meiosis", "protein", "enzim", 
                "bacteria", "virus", "inmune", "nervioso", "vida", "organismo",
                "mitocondria", "fotosíntesis", "respiración", "ecolog",
                "cell", "dna", "mitochondria", "life", "organism"
            ],
            "quimica": [
                "química", "quimica", "átomo", "atomo", "molécula", "molecula", 
                "reacción", "reaccion", "enlace", "estequiometría", "molar", 
                "solución", "ácido", "base", "ph", "electrón", "protón", "neutrón", 
                "tabla periódica", "orgánica", "inorgánica", "gas", "oxidación",
                "chemistry", "molecule", "reaction", "bond", "atom"
            ],
            "fisica": [
                "física", "fisica", "velocidad", "fuerza", "energía", "energia", 
                "vector", "cinemática", "dinámica", "newton", "trabajo", "potencia", 
                "termodinámica", "fluido", "onda", "luz", "sonido", "eléctrico", 
                "magnético", "circuito", "voltaje", "corriente", "gravedad",
                "physics", "force", "energy", "velocity", "kinematics"
            ],
            "matematicas": [
                "matemática", "calcul", "deriv", "integr", "ecuacion", "ecuación", 
                "numero", "álgebra", "algebra", "trigonometr", "sumar", "restar", 
                "multiplicar", "dividir", "logaritmo", "exponente", "soluci", 
                "suma", "resta", "angul", "ángulo", "geometr", "estadística", 
                "probabilidad", "función", "limite", 
                "math", "equation", "solve", "number"
            ],
            "sociales": [
                "historia", "guerra", "constitución", "siglo", "quién fue", 
                "colombia", "president", "revolución", "independencia", 
                "democracia", "derecho", "ciudadan", "imperio", "batalla", "gobierno", 
                "geografía", "mapa", "política", "economía",
                "history", "war", "century", "government", "geography"
            ],
            "lectura_critica": [
                "texto", "lectura", "crítica", "critica", "argumento", "tesis", 
                "autor", "inferencia", "conclusión", "párrafo", "intención", 
                "literario", "cuento", "ensayo", "poema", "gramática", "ortografía",
                "reading", "text", "argument", "thesis"
            ],
            "analisis_imagen": [
                "imagen", "figura", "vista", "perspectiva", "rotación", "rotacion", 
                "plano", "proyección", "isometría", "doblez", "patrón", "secuencia", 
                "espacial", "cubo", "armar", "desplegar",
                "image", "figure", "view", "perspective", "rotation"
            ],
            "ingles": [
                "traduc", "ingles", "english", "significado", "translate", "meaning", 
                "verb", "vocabulary", "speaking", "listening"
            ]
        }

    def determine_category(self, text: str) -> dict:
        """
        Main entry point. Returns a dict:
        {
            "category": "biologia" | "quimica" | "fisica" | "matematicas" | 
                        "sociales" | "lectura_critica" | "analisis_imagen" | "ingles" | "general",
            "source": "regex" | "ai"
        }
        """
        if not text:
            return {"category": "general", "source": "regex"}
            
        # --- STEP 1: FAST CHECK (Regex/Keywords) ---
        text_lower = text.lower()
        for category, keywords in self.keyword_map.items():
            if any(k in text_lower for k in keywords):
                logger.info(f"Router: Keyword match found for '{category}'")
                return {"category": category, "source": "regex"}
                
        # --- STEP 2: SMART CHECK (LLM Fallback) ---
        try:
            category = self._classify_with_llm(text)
            return {"category": category, "source": "ai"}
        except Exception as e:
            logger.warning(f"Router: LLM classification failed: {e}")
            return {"category": "general", "source": "error_fallback"}

    def _classify_with_llm(self, text: str) -> str:
        """
        Asks a small, fast model to classify the text.
        """
        # Define the valid categories for the AI
        categories = list(self.keyword_map.keys()) + ["general"]
        
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
            
            # Validate return value
            if category not in categories:
                logger.warning(f"Router: AI returned invalid category '{category}', defaulting to 'general'")
                return "general"
                
            logger.info(f"Router: AI classified as '{category}' using {router_model}")
            return category
            
        except Exception as e:
            logger.error(f"Router: Error calling OpenAI: {e}")
            raise e

# Singleton instance
semantic_router = SemanticRouter()