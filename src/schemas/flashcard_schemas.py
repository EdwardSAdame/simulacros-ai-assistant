# src/schemas/flashcard_schemas.py
"""
Defines the Pydantic schemas for flashcard generation.
These models are utilized to enforce strict JSON output schemas 
when communicating with the OpenAI API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional

class FlashcardItem(BaseModel):
    """
    Represents a single flashcard with a front (question/concept),
    a reasoning step to solve the question, and a back (short answer).
    """
    front: str = Field(
        ..., 
        description="The concept, question, or term to be placed on the front of the flashcard."
    )
    reasoning: str = Field(
        ...,
        description="A brief chain of thought to solve or answer the question on the front. This is an internal cognitive step and will not be displayed to the user."
    )
    back: str = Field(
        ..., 
        description="The short answer, definition, or explanation for the back of the flashcard. It MUST be extremely concise, ideally 1-3 words, and no more than a short sentence."
    )

class FlashcardsPayload(BaseModel):
    """
    Represents the complete payload returned by the AI, 
    containing metadata and the list of flashcards.
    """
    image_prompt: Optional[str] = Field(
        None,
        description=(
            "Instructions for a purely ORNAMENTAL and DECORATIVE illustration to set the mood for this flashcard deck. "
            "CRITICAL CONSTRAINTS: "
            "1. NO TEXT, NO LETTERS, NO NUMBERS, NO WORDS under any circumstances. "
            "2. NO DIAGRAMS, no charts, no maps, no literal academic representations. "
            "3. The image is strictly for aesthetic visual appeal. "
            "Use beautiful, atmospheric metaphors (e.g., classic Impressionist art, oil paintings of landscapes, nature, or 19th-century scenes) that loosely relate to the general theme."
        )
    )
    topic: str = Field(
        ..., 
        description="The specific academic topic these flashcards cover."
    )
    count: int = Field(
        ..., 
        description="The total number of flashcards generated."
    )
    cards: List[FlashcardItem] = Field(
        ..., 
        description="The list of flashcards generated for the user."
    )
    background_image: Optional[str] = Field(
        None,
        description="The S3 URL of the generated background illustration for this deck."
    )