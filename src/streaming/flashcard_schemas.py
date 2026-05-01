# src/schemas/flashcard_schemas.py
from pydantic import BaseModel, Field
from typing import List

class Flashcard(BaseModel):
    question: str = Field(
        description="The question, concept, or prompt to be displayed on the front of the flashcard."
    )
    answer: str = Field(
        description="The concise, accurate answer or explanation to be displayed on the back of the flashcard."
    )

class FlashcardDeck(BaseModel):
    flashcards: List[Flashcard] = Field(
        description="A collection of flashcards covering the requested topic."
    )