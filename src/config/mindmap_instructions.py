# src/config/mindmap_instructions.py

def build_mindmap_instructions(exam_context: str = "GENERAL") -> str:
    return """Your specific task is to deconstruct complex topics into highly structured, logical, and easy-to-understand mind maps.

You will output the data strictly adhering to the provided schema (nodes and edges). 

Follow these absolute rules for constructing the mind map:

1. DYNAMIC HIERARCHY AND ADAPTIVE DEPTH:
   - Level 0 (Root): Exactly ONE root node representing the central topic.
   - Level 1 (Branches): Major sub-categories. Determine the number of branches dynamically based on the natural structure and complexity of the topic.
   - Level 2+ (Sub-branches): Break down each branch into specific concepts, formulas, authors, or key facts.
   - Allow the depth to evolve naturally up to Level 4 or Level 5 if the topic demands it. Do not artificially truncate complex subjects, but avoid unnecessary deeper levels if the concept is simple.

2. CONCEPTUAL CLARITY OVER STRICT BREVITY (CRITICAL):
   - Node labels should be concise enough to fit in a visual diagram, but long enough to convey the exact meaning.
   - You are free to use short phrases to ensure the concept is perfectly understood. Do not oversimplify just to save space.

3. STRUCTURAL LOGIC:
   - Ensure every single node (except the root) has exactly one parent. Do not leave any floating or disconnected nodes.
   - Expand branches symmetrically where appropriate, but allow asymmetrical depth if one sub-topic is naturally more complex than the others.
"""