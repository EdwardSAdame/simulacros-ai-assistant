# src/services/signal_service.py
from src.services.context_builder import build_runtime_context
from src.config.system_instructions import build_system_instructions
from src.config.visual_instructions import build_visual_instructions

def build_runtime_signals(
    user_id: str | None, 
    page: str | None, 
    name: str | None, 
    email: str | None, 
    exam_context: str = "ICFES",
    requires_visuals: bool = False
) -> str:
    """Generates the dynamic system context for the AI."""
    
    signals = build_runtime_context(
        page=page,
        user_id=user_id, 
        name=name,
        email=email
    )

    if requires_visuals:
        visuals_trigger = (
            "VISUALS: Use the 'python' tool (Code Interpreter) to AUTOMATICALLY GENERATE PLOTS for any request involving "
            "mathematical functions, geometry, or data trends. Do not just describe the graph—DRAW IT. Output the file."
        )
        visual_style_guide = build_visual_instructions()
        signals.append(visuals_trigger)
        signals.append(visual_style_guide)
    
    return build_system_instructions(extras=signals, exam_context=exam_context)