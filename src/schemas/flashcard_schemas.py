# FILE: src/schemas/flashcard_schemas.py

from pydantic import BaseModel, Field
from typing import List

class FlashcardItem(BaseModel):
    front: str = Field(
        ..., 
        description="The concept, question, or term to be placed on the front of the flashcard."
    )
    back: str = Field(
        ..., 
        description="The detailed definition, answer, or explanation for the back of the flashcard."
    )

class FlashcardsPayload(BaseModel):
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