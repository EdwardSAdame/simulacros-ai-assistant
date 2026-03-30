# src/schemas/quiz_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class QuizOption(BaseModel):
    text: str = Field(..., description="The answer text. FORMATTING RULES: 1. If the answer is just words/text, write normally WITHOUT delimiters (e.g., 'La biomasa disminuye'). 2. If the answer is a number, equation, or symbol, wrap it in standard LaTeX delimiters \\( and \\). Example: '\\( -\\infty \\)' or '\\( 0 \\)'. 3. Mixed: 'El valor es \\( 5 \\)'. DO NOT double-escape backslashes.")
    feedback: str = Field(..., description="Short feedback explaining why this option is right/wrong.")

class QuizQuestion(BaseModel):
    question_title: str = Field(..., description="Title with number, e.g., '# 1. Topic'")
    
    # -------------------------------------------------------------------------
    # LOGIC ENGINE: Preserved 'THE SETUP' + Anti-Echo Constraint
    # -------------------------------------------------------------------------
    explanation: str = Field(..., description=(
        "Detailed reasoning plan. YOU MUST FOLLOW THIS STRUCTURE:\n"
        "1. THE SETUP: Define the EXACT numbers/facts you will use.\n"
        "2. THE SOLUTION: Solve the problem step-by-step using ONLY the setup.\n"
        "3. THE TRAPS: Identify 3 failure paths based on these specifics.\n"
        "CRITICAL RULE: DO NOT draft, echo, or repeat the question text, the options (A, B, C, D), or the correct answer index inside this field. Only write the Setup, Solution, and Traps."
    ))

    # REVERTED TO MATCH WIX UI: Kept token saving rule
    source_url: Optional[str] = Field(None, description="The exact URL of the web search. Put this ONLY in the FIRST question. Leave null for all subsequent questions to save tokens.")

    # REVERTED TO MATCH WIX UI: Kept token saving rule
    context_text: Optional[str] = Field(None, description="The full reading passage. Put this ONLY in the FIRST question. For subsequent questions, you MUST leave this as null to save tokens.")

    question_text: str = Field(..., description="The question stem. FORMATTING: Write regular text normally. Wrap ONLY math expressions, numbers, and symbols in standard LaTeX (\\( and \\)). Example: 'Si \\( x = 5 \\), que sucede?'. MUST match 'THE SETUP' numbers exactly.")
    
    # -------------------------------------------------------------------------
    # NEW: DECOUPLED IMAGE ARCHITECTURE
    # -------------------------------------------------------------------------
    image_prompt: Optional[str] = Field(None, description="If an illustration is needed for this question, provide a highly detailed text prompt describing the image you want generated (e.g., 'A Claude Monet style painting of...'). Leave null if no image is needed.")
    
    image_url: Optional[str] = Field(None, description="URL of the generated image/graph. If you wrote an image_prompt, LEAVE THIS NULL. The backend will populate it automatically. If you used the python code_interpreter, put the local file path here.")

    difficulty: Literal[1, 2, 3] = Field(1, description="Difficulty weight: 1 (Basic/Easy), 2 (Application/Medium), 3 (Analysis/Hard).")

    options: List[QuizOption] = Field(..., description="Exactly 4 options.")
    correct_option_index: Literal[0, 1, 2, 3] = Field(..., description="Index of the correct option (0-3).")

class QuizResponse(BaseModel):
    title: str = Field(..., description="A professional, short, engaging title for this quiz based on the specific topic (Max 6 words).")
    intro_message: str = Field(..., description="A single, concise sentence introducing the quiz (Voice: Roma).")
    question_count: int = Field(..., description="The total number of questions generated in this quiz.")
    questions: List[QuizQuestion]

    easier_payload: str = Field(..., description="A specific user command to generate an EASIER version of this quiz. E.g., 'Hazme un quiz mas facil sobre [Topic]'.")
    harder_payload: str = Field(..., description="A specific user command to generate a HARDER/ADVANCED version of this quiz. E.g., 'Hazme un examen avanzado sobre [Topic]'.")
    retry_payload: str = Field(..., description="A specific user command to generate a NEW quiz on the SAME TOPIC and SAME DIFFICULTY. E.g., 'Dame otro quiz sobre [Topic]'.")