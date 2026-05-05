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