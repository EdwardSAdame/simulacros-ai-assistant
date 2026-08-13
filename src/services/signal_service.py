from src.services.context_builder import build_runtime_context
from src.config.system_instructions import build_system_instructions

def build_runtime_signals(
    user_id: str | None, 
    page: str | None, 
    name: str | None, 
    email: str | None, 
    exam_context: str = "ICFES",
    requires_visuals: bool = False,
    intent: str = "chat",
    category: str = "general",
    custom_topic: str = "",
    is_document_grounded: bool = False
) -> str:
    """Generates the dynamic system context for the AI."""
    
    # 1. Build the base runtime context (date, user info, page context)
    signals = build_runtime_context(
        page=page,
        user_id=user_id, 
        name=name,
        email=email
    )

    # Block the Admission "Target Semester" logic from contaminating quizzes.
    # The quiz generator doesn't need to know about seasonality and cut-off scores.
    if intent == "quiz" and signals:
        signals = [s for s in signals if "TARGET SEMESTER" not in s]

    # 2. Delegate everything else to the smart builder.
    return build_system_instructions(
        extras=signals, 
        exam_context=exam_context,
        requires_visuals=requires_visuals,
        intent=intent,
        category=category,
        custom_topic=custom_topic,
        is_document_grounded=is_document_grounded
    )