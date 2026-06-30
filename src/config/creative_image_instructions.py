# src/config/creative_image_instructions.py

def get_creative_image_system_prompt() -> str:
    """
    Returns the token-optimized system instructions for image generation.
    Enforces the Invicto brand visual identity using strict positive constraints.
    """
    return (
        "- **Style Mandate (Claude Monet)**: The image must strictly follow the Impressionist style of Claude Monet. Apply visible brushstrokes, accurate depiction of changing light, ordinary subjects, movement, and unusual visual angles.\n"
        "- **Subject Mandate**: The illustration must be a purely artistic and atmospheric representation of a physical environment. Focus exclusively on natural landscapes, historical architecture, or tangible real-world scenes. The composition must rely solely on shapes, colors, lighting, and textures to convey meaning.\n"
    )