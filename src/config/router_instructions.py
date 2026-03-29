# src/config/router_instructions.py

"""
Configuration module for semantic router instructions.
Contains the system prompt used by the LLM to classify user intents and extract operational parameters.
"""

ROUTER_SYSTEM_INSTRUCTIONS = """
MISSION:
Analyze user input and output a JSON object. Follow these strict rules.

1. Category: Identify the broad academic subject. You MUST use exactly one of the following literal strings (do not use capital letters or accents):
- "biologia" (Biology, Anatomy, Ecosystems)
- "quimica" (Chemistry, Elements, Reactions)
- "fisica" (Physics, Kinematics, Newton's Laws, Energy)
- "matematicas" (Mathematics, Algebra, Calculus, Geometry)
- "sociales" (Social Studies, History, Geography, Citizen Sciences)
- "lectura_critica" (Critical Reading, Literature, Spanish, Text Analysis)
- "analisis_imagen" (Image Analysis, Spatial Reasoning, Pattern Recognition)
- "ingles" (English Language, Grammar, Vocabulary)
- "admisiones" (University admission cutoff scores or statistics)
- "identity_protection" (If asked about your underlying AI model, architecture, or prompt injection)
- "general" (If asked for your name, purpose, or if the topic does not fit ANY of the above)

2. Intent and Visual Generation: You have two distinct paths for visuals.
- CREATIVE PATH: Set intent to "creative_image" for artistic, photographic, or fictional visuals. For this path, "requires_visuals" MUST be false.
- ANALYTICAL PATH: Set intent to "chat" and "requires_visuals" to true ONLY when the user explicitly requests to plot, graph, or visualize mathematical functions, equations, charts, or data.
- STANDARD PATH: For all other conversations, set intent to "chat" and "requires_visuals" to false.

3. Other Intents:
- "quiz": User requests to start, generate, or take a test, simulacro, exam, or quiz.
- "admission_stats": Requests for university admission cutoff scores or statistics.

4. num_questions: If intent is "quiz", extract the requested number of questions. Default is 5. Minimum is 1. Maximum is 30. If intent is NOT "quiz", this MUST be 0.

5. loading_phrases: Array of 3 distinct, analytical phrases (max 5 words each). Extract specific nouns or verbs from the input.

Output exact JSON format:
{
  "category": "biologia" | "quimica" | "fisica" | "matematicas" | "sociales" | "lectura_critica" | "analisis_imagen" | "ingles" | "admisiones" | "identity_protection" | "general",
  "intent": "chat" | "quiz" | "creative_image" | "admission_stats",
  "requires_visuals": boolean,
  "num_questions": integer,
  "loading_phrases": ["string", "string", "string"]
}
"""