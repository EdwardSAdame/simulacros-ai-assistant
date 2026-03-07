# src/schemas/quiz_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class QuizOption(BaseModel):
    # FIX: Removed double-escape instruction. Now requests standard LaTeX.
    text: str = Field(..., description="The answer text. FORMATTING RULES: 1. If the answer is just words/text, write normally WITHOUT delimiters (e.g., 'La biomasa disminuye'). 2. If the answer is a number, equation, or symbol, wrap it in standard LaTeX delimiters \\( and \\). Example: '\\( -\\infty \\)' or '\\( 0 \\)'. 3. Mixed: 'El valor es \\( 5 \\)'. DO NOT double-escape backslashes.")
    feedback: str = Field(..., description="Short feedback explaining why this option is right/wrong.")

class QuizQuestion(BaseModel):
    question_title: str = Field(..., description="Title with number, e.g., '# 1. Topic'")
    
    # -------------------------------------------------------------------------
    # LOGIC ENGINE: Preserved 'THE SETUP' for deep thinking
    # -------------------------------------------------------------------------
    explanation: str = Field(..., description=(
        "Detailed reasoning plan. YOU MUST FOLLOW THIS STRUCTURE:\n"
        "1. THE SETUP: Define the EXACT numbers/facts you will use.\n"
        "2. THE SOLUTION: Solve the problem step-by-step using ONLY the setup.\n"
        "3. THE TRAPS: Identify 3 failure paths based on these specifics."
    ))

    # NEW: Context Text for Reading Comprehension
    context_text: Optional[str] = Field(None, description="The reading passage, historical context, or case study required to answer the question. USE ONLY IF the topic requires reading comprehension (e.g., 'Lectura Crítica', 'Inglés', 'Ciencias'). If the question is standalone (e.g., direct Math equation), leave this as null.")

    # FIX: Standard LaTeX delimiters
    question_text: str = Field(..., description="The question stem. FORMATTING: Write regular text normally. Wrap ONLY math expressions, numbers, and symbols in standard LaTeX (\\( and \\)). Example: 'Si \\( x = 5 \\), que sucede?'. MUST match 'THE SETUP' numbers exactly.")
    
    # EXISTING: Field for the Graph/Image URL
    image_url: Optional[str] = Field(None, description="URL of the generated image/graph. If you used the python tool to generate a graph, this will be populated.")

    # NEW: Weighted Scoring Logic
    difficulty: int = Field(1, ge=1, le=3, description="Difficulty weight: 1 (Basic/Easy), 2 (Application/Medium), 3 (Analysis/Hard).")

    options: List[QuizOption] = Field(..., min_items=4, max_items=4, description="Exactly 4 options.")
    correct_option_index: int = Field(..., ge=0, le=3, description="Index of the correct option (0-3).")

class QuizResponse(BaseModel):
    title: str = Field(..., description="A professional, short, engaging title for this quiz based on the specific topic (Max 6 words).")
    intro_message: str = Field(..., description="A single, concise sentence introducing the quiz (Voice: Roma).")
    question_count: int = Field(..., description="The total number of questions generated in this quiz.")
    questions: List[QuizQuestion]

    easier_payload: str = Field(..., description="A specific user command to generate an EASIER version of this quiz. E.g., 'Hazme un quiz mas facil sobre [Topic]'.")
    harder_payload: str = Field(..., description="A specific user command to generate a HARDER/ADVANCED version of this quiz. E.g., 'Hazme un examen avanzado sobre [Topic]'.")
    retry_payload: str = Field(..., description="A specific user command to generate a NEW quiz on the SAME TOPIC and SAME DIFFICULTY. E.g., 'Dame otro quiz sobre [Topic]'.")