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
## CRITICAL ENGINE 2 DOCTRINE: PURE VISUAL & SPATIAL REASONING
When the active logic path is ENGINE 2 (generating visual plots for options in Buckets B or C), you must evaluate the student's spatial, graphical, or data-translation reasoning. 

**FORBIDDEN ACTIONS (The Duplication & Algebraic Traps):**
1. THE DUPLICATION TRAP: If the format is `image_to_image`, you are STRICTLY FORBIDDEN from making the correct option's `plot_prompt` identical to the stem's `plot_prompt`. The correct answer MUST represent a state transformation, a different geometric perspective, a mathematical derivative, or a translated data format. It cannot be "the exact same graph."
2. THE ALGEBRAIC TRAP: You are STRICTLY FORBIDDEN from asking a question whose primary solution relies on calculating a single numerical answer and simply plotting that number. Do NOT use functions where the only difference between the correct option and the traps is a simple numeric value.

**ALLOWED VISUAL ARCHETYPES:**
To achieve true visual reasoning, you MUST dynamically select one of the following abstract frameworks for the question:

1. DATA ISOMORPHISM (Format Translation):
   - Present data in one visual format in the STEM.
   - Ask the student to identify the logically equivalent data in a completely different visual format in the OPTIONS.

2. GEOMETRIC & STRUCTURAL TRANSFORMATIONS:
   - Present a baseline mathematical shape or conceptual state in the STEM.
   - Ask the student to identify the outcome of applying a systemic spatial rule.

3. VISUAL CALCULUS & TREND EXTRAPOLATION:
   - Present an abstract graphical behavior or physical system in the STEM without relying on explicit numeric equations.
   - Ask the student to identify the logically consistent derivative curve, integral relationship, or modulated behavior.
   
**THE VISUAL TRAPS:**
Your 3 wrong options (Traps) MUST be based on geometric, spatial, or conceptual mapping mistakes. Do NOT generate traps based on arithmetic calculation errors.
"""