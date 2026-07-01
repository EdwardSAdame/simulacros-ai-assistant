# src/config/exam_reasoning_doctrine.py

"""
EXAM REASONING DOCTRINE (Cognitive Framework)
Context: Defines the cognitive rules and pedagogical constraints for the AI's logic engines.
This file focuses purely on *how the AI should think*, keeping it strictly separated
from *how the AI should draw* (which is handled in visual_instructions.py).
"""

VISUAL_REASONING_DOCTRINE = """
## CRITICAL ENGINE 2 DOCTRINE: PURE VISUAL & SPATIAL REASONING
When the active logic path is ENGINE 2 (generating visual plots for options in Buckets B or C), you must evaluate the student's spatial, graphical, or data-translation reasoning. 

**FORBIDDEN ACTIONS (The Algebraic Trap):**
You are STRICTLY FORBIDDEN from asking a question whose primary solution relies on calculating a single numerical answer (like solving y=mx+b, finding a missing coordinate, or extending a simple line) and simply plotting that number. Do NOT use functions where the only difference between the correct option and the traps is a simple numeric intercept or slope.

**ALLOWED VISUAL ARCHETYPES:**
To achieve true visual reasoning, you MUST dynamically select one of the following abstract frameworks for the question:

1. DATA ISOMORPHISM (Format Translation):
   - Present data in one visual format in the STEM (e.g., a complex curve, a raw data distribution, or a conceptual scatter).
   - Ask the student to identify the logically equivalent data in a completely different visual format in the OPTIONS (e.g., a histogram, a pie chart, a density plot, or a bar chart).

2. GEOMETRIC & STRUCTURAL TRANSFORMATIONS:
   - Present a baseline mathematical shape or conceptual state in the STEM.
   - Ask the student to identify the outcome of applying a systemic spatial rule.
   - Example: The STEM shows a generic function f(x). The OPTIONS show reflections across axes, topological translations like f(x-c), scaling, or symmetries.

3. VISUAL CALCULUS & TREND EXTRAPOLATION:
   - Present an abstract graphical behavior or physical system in the STEM without relying on explicit numeric equations.
   - Ask the student to identify the logically consistent derivative curve, integral relationship, or modulated behavior.
   - Example: "Which graph best represents the rate of change (velocity) of the function shown above?", or "How would this wave structure change if its frequency were doubled?"

**THE VISUAL TRAPS:**
Your 3 wrong options (Traps) MUST be based on geometric, spatial, or conceptual mapping mistakes (e.g., shifting left instead of right, reflecting across the wrong axis, inverting concavity, or mapping X data to the Y axis). Do NOT generate traps based on arithmetic calculation errors.
"""