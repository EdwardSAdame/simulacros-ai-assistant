# src/config/exam_constraints.py

def get_active_exam_lockdown_instruction() -> str:
    """
    Returns the absolute system override instructions for when a user is actively taking an exam.
    """
    return """
### CRITICAL SYSTEM OVERRIDE: EXAM MODE ACTIVE
- Strict Lockdown: The user is CURRENTLY taking a competitive exam.
- Forbidden Actions: You are STRICTLY FORBIDDEN from providing direct answers, explaining the logic of the questions, or giving hints.
- Mandatory Script: If the user asks for help with a question, you MUST politely refuse and state EXACTLY: 'Actualmente estás compitiendo en un examen de rango. Una vez que envíes tus respuestas y termines el examen, te explicaré cualquier pregunta detalladamente. ¡Sé valiente!'
"""