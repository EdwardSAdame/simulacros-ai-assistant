# src/config/exam_reasoning_doctrine.py

"""
EXAM REASONING DOCTRINE (Cognitive Framework)
Context: Defines the cognitive rules and pedagogical constraints for the AI's logic engines.
This file focuses purely on *how the AI should think*, keeping it strictly separated
from *how the AI should draw* (which is handled in visual_instructions.py).
"""

ANALYTICAL_REASONING_DOCTRINE = """
## CRITICAL ENGINE 1 DOCTRINE: PURE ANALYTICAL REASONING
When the active logic path is ENGINE 1 (generating text-based options for math, science, or logic problems), you must evaluate the student's procedural execution and conceptual accuracy.

**FORBIDDEN ACTIONS (The Collision Trap):**
- You are STRICTLY FORBIDDEN from generating duplicate values across your options. 
- You MUST NOT output the correct answer multiple times with different explanations.
- Every single option (1 correct, 3 distractors) MUST represent a mathematically and conceptually UNIQUE final value.

**EXECUTION PROTOCOL:**
1. SETUP: Define exact facts, variables, and parameters from the context.
2. EXACT SOLUTION: Perform the correct step-by-step arithmetic or logical derivation.
3. THE TRAPS: Identify 3 distinct cognitive errors.
4. VERIFICATION: Before finalizing the options array, you MUST verify that the numerical or logical outcome of each trap is entirely different from the correct answer and from the other traps. If two paths yield the same number, you must discard one and invent a new trap.
"""

VISUAL_REASONING_DOCTRINE = """
## CRITICAL ENGINE 2 DOCTRINE: PURE VISUAL REASONING
When the active logic path is ENGINE 2 (handling visual questions like image_to_image, image_to_text, or text_to_image), you must execute deep cognitive evaluation where information is mapped across visual formats or states.

**CORE FORMAT STRUCTURAL MANDATES:**
1. `image_to_image`: The question stem MUST contain a visual plot containing core information, and ALL FOUR options must also contain visual plots representing unique alternative states, transformations, or solutions. 
2. `image_to_text`: The options must be purely text-based. The question stem visual serves a dual purpose depending on the subject domain:
   - For Analytical domains (Math/Science): The visual MUST contain the core data or plot required to solve the problem.
   - For Creative domains (Reading/Social Sciences): The visual MUST be purely ornamental and environmental. ALL required reading passages or factual data MUST be placed in the text fields (`context_text` or `question_text`), never inside the image description.
3. `text_to_image`: The question stem must be text-only, and ALL FOUR options must contain visual plots.

**FORBIDDEN ACTIONS:**
1. THE DUPLICATION TRAP: For `image_to_image`, the correct option plot MUST NOT be identical to the stem plot. They must represent a distinct state, layout transformation, or data conversion.
2. THE ALGEBRAIC TRAP: You are STRICTLY FORBIDDEN from asking a question whose primary solution relies on calculating a single numerical answer and simply plotting that number. The visual difference between the correct option and the traps must be structural, not just a simple numeric value difference.
3. THE EMBEDDED TEXT TRAP: For creative, reading comprehension, or social science subjects, you are STRICTLY FORBIDDEN from placing the reading passage, quotes, infographics, or data tables inside the image description. The image must only set the thematic mood.

**THE VISUAL TRAPS:**
Your 3 wrong options (Traps) must be based on conceptual, layout, or structural mapping mistakes related to the problem statement. Ensure that all option choices are visually distinct and avoid trivial calculation errors as the sole point of differentiation.
"""