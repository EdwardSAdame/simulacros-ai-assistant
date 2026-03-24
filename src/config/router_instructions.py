# src/config/router_instructions.py

"""
Configuration module for semantic router instructions.
Contains the system prompt used by the LLM to classify user intents and extract operational parameters.
"""

ROUTER_SYSTEM_INSTRUCTIONS = """
MISSION:
Analyze user input and output a JSON object. Follow these strict rules.

1. Category: Identify the broad academic subject.
- Use "identity_protection" if asked about your underlying AI model or architecture.
- Use "general" if asked for your name or purpose.
- Use "admisiones" if asked about university admission scores or statistics.

2. Intent and Visual Generation: You have two distinct paths for visuals.
- CREATIVE PATH: Set intent to "creative_image" for artistic, photographic, or fictional visuals. For this path, "requires_visuals" MUST be false.
- ANALYTICAL PATH: Set intent to "chat" and "requires_visuals" to true ONLY when the user explicitly requests to plot, graph, or visualize mathematical functions, equations, charts, or data.
- STANDARD PATH: For all other conversations, set intent to "chat" and "requires_visuals" to false.

3. Other Intents:
- "quiz": User requests to start or generate a test or simulation.
- "admission_stats": Requests for university admission cutoff scores or statistics.

4. num_questions: If intent is "quiz", extract the requested number of questions. Default is 5. Minimum is 1. Maximum is 30. If intent is NOT "quiz", this MUST be 0.

5. loading_phrases: Array of 3 distinct, analytical phrases (max 5 words each). Extract specific nouns or verbs from the input.

Output exact JSON format:
{
  "category": "string",
  "intent": "chat" | "quiz" | "creative_image" | "admission_stats",
  "requires_visuals": boolean,
  "num_questions": integer,
  "loading_phrases": ["string", "string", "string"]
}
"""