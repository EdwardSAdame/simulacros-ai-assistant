# src/config/router_instructions.py

"""
Configuration module for semantic router instructions.
Contains the dynamic system prompt used by the LLM to classify user intents based on the active exam context.
"""

def build_router_instructions(exam_context: str, current_activity: str = "chat") -> str:
    """
    Dynamically generates the routing taxonomy based on the active exam context and sticky UI state.
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

=== SYSTEM STATE & CRITICAL OVERRIDES ===
CURRENT_ACTIVITY: "{current_activity}"

CRITICAL ALGORITHMIC OVERRIDE (AMNESIA PREVENTION):
IF CURRENT_ACTIVITY is NOT "chat" (e.g., "quiz", "flashcards") AND the user's input is short (under 6 words) or contains a bare number (e.g., "la 5", "el 3", "pregunta 4", "siguiente"):
THEN you MUST strictly output:
- "intent": "chat"
- "num_questions": 0
UNDER NO CIRCUMSTANCES should you output "quiz" or "flashcards" for a short numeric input. You may ONLY route to a generation intent if the user uses explicit creation verbs (e.g., "crea un nuevo simulacro", "dame otro quiz", "generar").

1. INTENT CLASSIFICATION: Classify the user's goal using exactly one of these strings. Evaluate this BEFORE category mapping:
- "chat": Standard conversational inquiries, explanations, analytical plotting, data visualization, diagram generation from data, tabular data generation, general statements, OR follow-ups regarding the CURRENT_ACTIVITY. If the user requests to generate any analytical or structural graphic based on context, it MUST route here.
- "quiz": User EXPLICITLY wants to GENERATE a NEW test, exam, simulacro, or practice session. (Subject to the Critical Algorithmic Override above).
- "flashcards": User EXPLICITLY wants to learn facts, review, or memorize information quickly using NEW flashcards, cards, or spaced repetition.
- "mentalMap": User EXPLICITLY asks to visualize information through a NEW mind map, conceptual map, or structural diagram.
- "creative_image": User EXPLICITLY wants to generate an artistic, photorealistic, or fictional image. NEVER use this intent for any form of analytical data visualization, structural diagram, or mathematical plotting.
- "admission_stats": User wants university admission cutoff scores or data.

2. CATEGORY CLASSIFICATION: Identify the broad academic subject. Map specific sub-concepts to their parent discipline. You MUST use exactly one of these literal strings:
{categories}.

CRITICAL CATEGORY RULES:
- SUBJECT PRIORITY: If the user mentions ANY specific subject or topic, you MUST route to that specific category, even if they use words like "simulacro" or "examen".
- "general": You MUST use this category ONLY if the user asks for a broad, multi-subject exam WITHOUT specifying any subject at all.
- "admisiones": You MUST use this EXCLUSIVELY if the user asks for historical cutoff scores, admission statistics, or university data. NEVER use this category for a quiz.

3. VISUALS FLAG (requires_visuals): 
- ROLEPLAY AS AN EXPERT TUTOR: Think, "If I were explaining this concept to a student in a physical classroom, would I instinctively walk over and draw a graph, chart, data table, or spatial diagram on the whiteboard to give them a visual example?"
- Set to true if the query involves analyzing functions, statistical distributions, probabilities, data trends, physical kinematics, OR formatting structured data into visual tables where a graphical representation drastically improves human understanding.

4. QUANTITY EXTRACTION (num_questions): 
- If intent is "quiz", extract the requested QUANTITY of questions to generate (min 1, max 30).
- If intent is "flashcards", extract the requested number of flashcards (min 1, max 30).
- If intent is "chat" or any other non-generation intent, this MUST be 0. Do NOT extract a number if you are not generating a quiz or flashcards.

5. LOADING PHRASES (loading_phrases): 
- Generate an array of 3 distinct, analytical phrases (max 5 words each) extracting key nouns or verbs from the input.
"""