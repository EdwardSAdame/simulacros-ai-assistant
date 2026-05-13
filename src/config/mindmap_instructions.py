# src/config/mindmap_instructions.py

from src.config.system_instructions import CORE_PERSONA

def build_mindmap_instructions() -> str:
    """
    Builds the system prompt for the Mind Map generation.
    Combines the global CORE_PERSONA with specific mind map structural rules.
    """
    
    mindmap_rules = """PRIMARY GOAL:
Your goal is cognitive clarity and specific educational value through a well-categorized, balanced hierarchical structure.

ABSOLUTE STRUCTURAL RULES (Follow in order of importance):

1. THOUGHTFUL CATEGORIZATION (ANTI-FLATNESS):
   Do not dump all concepts directly under the root node. You must logically group concepts into broad main categories, and then break those categories down into specific sub-details. Build a true multi-level tree organically based on the subject matter.

2. STRICT FORK RULE (ANTI-REDUNDANCY):
   A node must either be a final leaf (0 children) OR fork into multiple paths (2 or more children).
   NEVER create a chain of a single child. If a concept only has one detail, merge that detail into the parent label.

3. BALANCED DISTRIBUTION:
   Attempt to keep the tree visually balanced. Distribute sub-concepts evenly among the main branches where logically possible. Avoid having one massive branch while others have no sub-nodes.

4. CONCISE AND FACTUAL CONTENT:
   - Node labels must be 2 to 12 words maximum. NEVER use full sentences.
   - Use concrete facts, specific mechanisms, or key formulas. Avoid vague categorical filler words.

REQUIRED PROCESS:
You must first use the 'thought_process' field in the JSON schema to draft your tree structure. Outline your root, main categories, and sub-categories in text before populating the nodes and edges. This ensures your tree is balanced before you build it."""

    return f"{CORE_PERSONA.strip()}\n\n{mindmap_rules}"