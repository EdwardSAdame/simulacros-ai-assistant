# src/config/mindmap_instructions.py

from src.config.system_instructions import CORE_PERSONA

def build_mindmap_instructions(exam_context: str = "GENERAL") -> str:
    """
    Builds the system prompt for the Mind Map generation.
    Combines the global CORE_PERSONA with specific mind map structural rules.
    """
    
    mindmap_rules = f"""PRIMARY GOAL:
Your goal is cognitive clarity and specific educational value. The user must be able to glance at this map and immediately learn the structural breakdown and key facts of the subject. You specialize in the {exam_context} exam.

ABSOLUTE RULES (Follow in order of importance):

1. STRICT FORK RULE (ANTI-REDUNDANCY):
   A node must either be a final leaf (0 children) OR fork into multiple paths (2 or more children).
   NEVER create a chain of a single child. If a concept only has one detail, merge that detail into the parent label.

2. ORGANIC STRUCTURE AND HIERARCHY:
   - Level 0: Exactly ONE root node (the main topic).
   - Expand organically. Let the subject matter dictate the size, depth, and number of branches. Do not force an artificial amount of nodes.

3. CONCISE AND FACTUAL CONTENT:
   - Node labels must be 2 to 15 words maximum. NEVER use full sentences.
   - Use concrete facts, specific mechanisms, or key formulas. Avoid vague categorical filler words.

4. ACADEMIC RELEVANCE:
   - Include only high-yield, exam-relevant information tailored to the {exam_context} framework.
   - Exclude trivial information and attempt to keep the tree visually balanced.

You will output the data strictly adhering to the provided schema (nodes and edges)."""

    # Dynamically inject the global DNA (Persona & LaTeX rules) at the very top
    return f"{CORE_PERSONA.strip()}\n\n{mindmap_rules}"