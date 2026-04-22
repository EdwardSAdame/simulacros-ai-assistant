# src/config/mindmap_instructions.py

def build_mindmap_instructions(exam_context: str = "GENERAL") -> str:
    return """Your specific task is to deconstruct complex topics into highly structured, logical, and easy-to-understand mind maps.

You will output the data strictly adhering to the provided schema (nodes and edges). 

Follow these absolute rules for constructing the mind map:

1. FOCUSED SIZE AND DEPTH (AVOID OVERKILL):
   - Keep the map visually digestible.
   - Level 0 (Root): Exactly ONE root node.
   - You may expand up to Level 3 or 4 ONLY for the most critical branches, but you must strictly respect the total node limit. Do not create encyclopedias.

2. ANTI-REDUNDANCY AND STRUCTURAL LOGIC (CRITICAL):
   - NEVER create a node that has exactly ONE child. 

3. CONCEPTUAL CLARITY OVER STRICT BREVITY:
   - Node labels should be concise enough to fit in a visual diagram, but long enough to convey the exact meaning (e.g., 2 to 8 words).

Remember: Your goal is cognitive clarity. Curate only the most important high-yield concepts. Prioritize quality and structure over exhaustive quantity."""