# src/services/semantic_router.py
import logging
import json
from src.config.settings import settings, get_openai_client

logger = logging.getLogger(__name__)

class SemanticRouter:
    """
    Determines the intent/category of a user message and extracts the main topic.
    Returns a dict with 'category', 'topic', and 'source'.
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
            "category": "biologia" | ... | "general",
            "topic": str (e.g., "mitochondria" or "nostalgia"),
            "source": "regex" | "ai"
        }
        """
        if not text:
            return {"category": "general", "topic": "general", "source": "regex"}
            
        # --- STEP 1: FAST CHECK (Regex/Keywords) ---
        text_lower = text.lower()
        for category, keywords in self.keyword_map.items():
            for k in keywords:
                if k in text_lower:
                    logger.info(f"Router: Keyword match found for '{category}' -> '{k}'")
                    # Return the specific keyword found as the topic
                    return {"category": category, "topic": k, "source": "regex"}
                
        # --- STEP 2: SMART CHECK (LLM Extraction) ---
        try:
            result = self._classify_with_llm(text)
            return {
                "category": result.get("category", "general"),
                "topic": result.get("topic", "general"),
                "source": "ai"
            }
        except Exception as e:
            logger.warning(f"Router: LLM classification failed: {e}")
            # Fallback
            return {"category": "general", "topic": "general", "source": "error_fallback"}

    def _classify_with_llm(self, text: str) -> dict:
        """
        Asks a small, fast model to classify the text AND extract the main subject.
        Returns: {"category": "...", "topic": "..."}
        """
        categories = list(self.keyword_map.keys()) + ["general"]
        router_model = settings.OPENAI_ROUTER_MODEL
        
        # We force the model to return JSON for easier parsing
        system_prompt = (
            f"You are a semantic classifier. "
            f"1. Classify the input into one of these categories: {', '.join(categories)}. "
            f"2. Extract the main subject/topic (max 3 words) of the user's query (e.g. 'nostalgia', 'quadratic equation'). "
            f"Return JSON format: {{ 'category': '...', 'topic': '...' }}."
        )

        try:
            response = self.client.chat.completions.create(
                model=router_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=45, 
                temperature=0.0,
                response_format={"type": "json_object"} # Ensures valid JSON
            )
            
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            category = data.get("category", "general").lower()
            topic = data.get("topic", "context").strip()

            if category not in categories:
                category = "general"

            logger.info(f"Router: AI classified as '{category}' with topic '{topic}'")
            return {"category": category, "topic": topic}
            
        except Exception as e:
            logger.error(f"Router: Error calling OpenAI: {e}")
            raise e

# Singleton instance
semantic_router = SemanticRouter()