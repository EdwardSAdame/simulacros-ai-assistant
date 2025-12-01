# src/services/semantic_router.py
import logging
import json
from src.config.settings import settings, get_openai_client

logger = logging.getLogger(__name__)

class SemanticRouter:
    """
    Determines the intent/category of a user message and generates dynamic
    visual feedback phrases.
    Returns a dict with 'category', 'loading_phrases', and 'source'.
    """
    
    def __init__(self):
        self.client = get_openai_client()
        
        # 1. Define categories and their keywords
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
        Main entry point. Returns:
        {
            "category": str,
            "loading_phrases": [str, str, str],
            "source": "regex" | "ai" | "fallback"
        }
        """
        if not text:
            return {
                "category": "general", 
                "loading_phrases": ["Procesando...", "Esperando datos..."], 
                "source": "regex"
            }
            
        # --- STEP 1: FAST CHECK (Regex/Keywords) ---
        text_lower = text.lower()
        for category, keywords in self.keyword_map.items():
            for k in keywords:
                if k in text_lower:
                    logger.info(f"Router: Keyword match found for '{category}' -> '{k}'")
                    # Create semi-dynamic phrases based on the keyword found
                    phrases = [
                        f"Detectando concepto: {k}...",
                        f"Consultando base de {category}...",
                        "Optimizando respuesta..."
                    ]
                    return {"category": category, "loading_phrases": phrases, "source": "regex"}
                
        # --- STEP 2: SMART CHECK (LLM Generation) ---
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
                "loading_phrases": ["Analizando contexto...", "Generando respuesta..."],
                "source": "error_fallback"
            }

    def _classify_with_llm(self, text: str) -> dict:
        """
        Asks the AI to classify AND generate creative status messages.
        """
        categories = list(self.keyword_map.keys()) + ["general"]
        router_model = settings.OPENAI_ROUTER_MODEL
        
        # Prompt designed for creativity and awareness of the user's language
        system_prompt = (
            f"You are the brain of an advanced AI tutor named Roma. "
            f"1. Classify the input into one of: {', '.join(categories)}. "
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
                max_tokens=80, 
                temperature=0.7, # Slightly higher temp for creativity
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            category = data.get("category", "general").lower()
            if category not in categories:
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