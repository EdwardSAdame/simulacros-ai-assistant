# src/config/creative_image_instructions.py

def get_creative_image_system_prompt() -> str:
    """
    Returns the strict, token-optimized system instructions for image generation.
    Enforces the Invicto brand visual identity and image format using Markdown.
    """
    return (
        "- **Style Mandate (Claude Monet)**: ALL images MUST strictly follow the Impressionist style of Claude Monet. Apply visible brushstrokes, accurate depiction of changing light, ordinary subjects, movement, and unusual visual angles.\n"
    )