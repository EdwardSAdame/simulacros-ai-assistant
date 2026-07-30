# Backend: simulacros-ai-assistant
# File: src/config/arena_instructions.py

from typing import List, Optional

def build_arena_system_instructions(
    arena_title: str, 
    arena_instructions: str, 
    runtime_signals: Optional[List[str]] = None
) -> str:
    """
    Constructs the system prompt specifically for Arena contexts.
    Enforces formatting rules and strict file_search tool usage.
    """
    
    base_tech_prompt = (
        "You are an advanced AI Assistant operating within a specific 'Arena' (knowledge workspace).\n\n"
        "OUTPUT RULES:\n"
        "- Use Markdown for formatting.\n"
        "- Use LaTeX for math equations.\n"
        "- Be helpful, clear, and accurate.\n\n"
        "CRITICAL TOOL INSTRUCTION:\n"
        "You have access to a file_search tool containing specific documents uploaded by the user for this Arena. "
        "You MUST prioritize querying the file_search tool to retrieve context before attempting to answer based on your general training data, even if the user's question seems broad or general. "
        "Base your responses primarily on the retrieved documents whenever applicable.\n"
    )

    if runtime_signals:
        context_str = "\n".join(runtime_signals)
        base_tech_prompt += f"\nCONTEXT:\n{context_str}\n"

    injection = f"\n\n## Identity: {arena_title}\n{arena_instructions}"
    
    return base_tech_prompt + injection