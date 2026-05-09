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
Analyze user input AND the conversation history to output a strict JSON object. Use your universal knowledge to semantically route the query to the correct domain. Pay close attention to context from previous turns.

1. Category: Identify the broad academic subject. Map specific sub-concepts to their parent discipline. You MUST use exactly one of these literal strings:
{categories}.

CRITICAL CATEGORY RULES:
- SUBJECT PRIORITY: If the user mentions ANY specific subject or topic (e.g., "ciencias", "biologia", "matematicas", "lectura"), you MUST route to that specific category, even if they use words like "simulacro" or "examen".
- "general": You MUST use this category ONLY if the user asks for a broad, multi-subject exam WITHOUT specifying any subject at all.
- "admisiones": You MUST use this EXCLUSIVELY if the user asks for historical cutoff scores, admission statistics, or university data. NEVER use this category for a quiz.

2. Intent: Classify the user's goal using exactly one of these strings:
- "quiz": User EXPLICITLY wants to GENERATE a test, exam, simulacro, or practice session. DO NOT use this intent if the user is asking to explain, solve, or review a specific question from previous messages.
- "flashcards": User EXPLICITLY wants to learn facts, review, or memorize information quickly using flashcards, cards, or spaced repetition.
- "mentalMap": User EXPLICITLY asks to visualize information through a mind map, conceptual map, or structural diagram.
- "creative_image": User wants to generate an artistic or fictional image.
- "admission_stats": User wants university admission cutoff scores or data.
- "chat": Standard conversational inquiries, explanations, analytical plotting, general statements, OR follow-up requests to explain or solve a specific question number.

3. Visuals (requires_visuals): 
- true ONLY if intent is "chat" AND the user's query involves a mathematical, spatial, physical, or data-driven concept where a visual graph, plot, or geometric representation would significantly enhance pedagogical comprehension.
- false for purely theoretical, historical, grammatical, or textual queries that do not fundamentally benefit from a mathematical plot or spatial diagram.

4. num_questions: 
- If intent is "quiz", extract the requested QUANTITY of questions to generate (default 5, min 1, max 30).
- If intent is "flashcards", extract the requested number of flashcards (default 10, min 1, max 30).
- If intent is NOT "quiz" or "flashcards", this MUST be 0.

5. loading_phrases: 
- Generate an array of 3 distinct, analytical phrases (max 5 words each) extracting key nouns or verbs from the input.
"""