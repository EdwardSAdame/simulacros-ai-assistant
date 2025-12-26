# src/schemas/quiz_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class QuizOption(BaseModel):
    # 🟢 CHANGED: Request \( ... \) explicitly
    text: str = Field(..., description="The answer text. Use '\\(' and '\\)' for inline LaTeX math.")
    feedback: str = Field(..., description="Short feedback explaining why this option is right/wrong.")

class QuizQuestion(BaseModel):
    question_title: str = Field(..., description="Title with number, e.g., '# 1. Topic'")
    # 🟢 CHANGED: Request \( ... \) explicitly
    question_text: str = Field(..., description="The question stem. Use '\\(' and '\\)' for inline LaTeX math, and '\\[' and '\\]' for block math.")
    
    # 🟢 EXISTING: Field for the Graph/Image URL
    image_url: Optional[str] = Field(None, description="URL of the generated image/graph. If you used the python tool to generate a graph, this will be populated.")

    # 🟢 NEW: Weighted Scoring Logic
    difficulty: int = Field(1, ge=1, le=3, description="Difficulty weight: 1 (Basic/Easy), 2 (Intermediate/Medium), 3 (Advanced/Hard).")

    options: List[QuizOption] = Field(..., min_items=4, max_items=4, description="Exactly 4 options.")
    correct_option_index: int = Field(..., ge=0, le=3, description="Index of the correct option (0-3).")
    explanation: str = Field(..., description="General explanation of the solution.")

class QuizResponse(BaseModel):
    intro_message: str = Field(..., description="A single, concise sentence introducing the quiz (Voice: Roma).")
    questions: List[QuizQuestion]