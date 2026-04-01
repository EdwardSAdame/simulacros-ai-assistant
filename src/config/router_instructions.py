# src/config/router_instructions.py

"""
Configuration module for semantic router instructions.
Contains the dynamic system prompt used by the LLM to classify user intents based on the active exam context.
"""

def build_router_instructions(exam_context: str) -> str:
    """
    Dynamically generates the routing taxonomy based on the active exam context.
    """
    
    # 1. UNAL MATRIX
    if exam_context == "UNAL":
        categories = '"matematicas", "ciencias_naturales", "analisis_textual", "ciencias_sociales", "analisis_imagen", "admisiones", "identity_protection", "general"'
    
    # 2. ICFES MATRIX
    elif exam_context == "ICFES":
        categories = '"matematicas", "ciencias_naturales", "lectura_critica", "sociales_ciudadanas", "ingles", "admisiones", "identity_protection", "general"'
    
    # 3. GENERAL MATRIX (Union of both, used for discovery)
    else:
        categories = '"matematicas", "ciencias_naturales", "analisis_textual", "ciencias_sociales", "analisis_imagen", "lectura_critica", "sociales_ciudadanas", "ingles", "admisiones", "identity_protection", "general"'

    return f"""MISSION:
Analyze user input and output a strict JSON object. Use your universal knowledge to semantically route the query to the correct domain.

1. Category: Identify the broad academic subject. Map specific sub-concepts to their parent discipline. You MUST use exactly one of these literal strings:
{categories}.

CRITICAL CATEGORY RULES:
- SUBJECT PRIORITY: If the user mentions ANY specific subject or topic (e.g., "ciencias", "biologia", "matematicas", "lectura"), you MUST route to that specific category, even if they use words like "simulacro" or "examen".
- "general": You MUST use this category ONLY if the user asks for a broad, multi-subject exam WITHOUT specifying any subject at all (e.g., "dame un simulacro completo", "quiero practicar para el icfes").
- "admisiones": You MUST use this EXCLUSIVELY if the user asks for historical cutoff scores, admission statistics, or university data (e.g., "puntaje de corte para medicina"). NEVER use this category for a quiz.

2. Intent: Classify the user's goal using exactly one of these strings:
- "quiz": User wants to take a test, exam, or simulacro.
- "creative_image": User wants to generate an artistic or fictional image.
- "admission_stats": User wants university admission cutoff scores or data.
- "chat": Standard conversational inquiries, explanations, or analytical plotting.

3. Visuals (requires_visuals): 
- true ONLY if intent is "chat" AND the user explicitly asks to plot, graph, or visualize mathematical functions or data.
- false for all other scenarios.

4. num_questions: 
- If intent is "quiz", extract the requested number of questions (default 5, min 1, max 30).
- If intent is NOT "quiz", this MUST be 0.

5. loading_phrases: 
- Generate an array of 3 distinct, analytical phrases (max 5 words each) extracting key nouns or verbs from the input.
"""