# src/services/signal_service.py
from src.services.context_builder import build_runtime_context
from src.config.system_instructions import build_system_instructions

def build_runtime_signals(
    user_id: str | None, 
    page: str | None, 
    name: str | None, 
    email: str | None, 
    exam_context: str = "ICFES",
    requires_visuals: bool = False
) -> str:
    """Generates the dynamic system context for the AI."""
    
    # 1. Build the base runtime context (date, user info, page context)
    signals = build_runtime_context(
        page=page,
        user_id=user_id, 
        name=name,
        email=email
    )

    # 2. Delegate everything else to the smart builder.
    # We pass requires_visuals directly so system_instructions.py handles it cleanly.
    return build_system_instructions(
        extras=signals, 
        exam_context=exam_context,
        requires_visuals=requires_visuals
    )