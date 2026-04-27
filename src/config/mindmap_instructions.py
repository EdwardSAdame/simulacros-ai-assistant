# src/config/mindmap_instructions.py

from src.config.system_instructions import CORE_PERSONA
from src.config.exam_frameworks import get_mindmap_domain_framework

def build_mindmap_instructions(exam_context: str = "GENERAL", category: str = "general") -> str:
    """
    Builds the system prompt for the Mind Map generation.
    Combines the global CORE_PERSONA, specific syllabus topics, and structural rules.
    """
    
    # Surgically extract only the academic topics for this specific subject
    domain_syllabus = get_mindmap_domain_framework(exam_context, category)
    
    syllabus_section = ""
    if domain_syllabus:
        syllabus_section = f"\nACADEMIC SYLLABUS & FOCUS:\nEnsure the mind map reflects the depth and specific topics outlined here:\n{domain_syllabus}\n"
    
    mindmap_rules = f"""PRIMARY GOAL:
Your goal is cognitive clarity and specific educational value. The user must be able to glance at this map and immediately learn the structural breakdown and key facts of the subject. You specialize in the {exam_context} exam.
{syllabus_section}
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