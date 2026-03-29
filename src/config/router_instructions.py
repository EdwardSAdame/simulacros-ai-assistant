# src/config/router_instructions.py

"""
Configuration module for semantic router instructions.
Contains the system prompt used by the LLM to classify user intents and extract operational parameters.
"""

ROUTER_SYSTEM_INSTRUCTIONS = """
MISSION:
Analyze user input and output a strict JSON object. Use your universal knowledge to semantically route the query to the correct domain.

1. Category: Identify the broad academic subject. Map specific sub-concepts to their parent discipline. You MUST use exactly one of these literal strings:
"biologia", "quimica", "fisica", "matematicas", "sociales", "lectura_critica", "analisis_imagen", "ingles", "admisiones", "identity_protection", or "general".

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

Output exact JSON format:
{
  "category": "biologia" | "quimica" | "fisica" | "matematicas" | "sociales" | "lectura_critica" | "analisis_imagen" | "ingles" | "admisiones" | "identity_protection" | "general",
  "intent": "chat" | "quiz" | "creative_image" | "admission_stats",
  "requires_visuals": boolean,
  "num_questions": integer,
  "loading_phrases": ["string", "string", "string"]
}
"""