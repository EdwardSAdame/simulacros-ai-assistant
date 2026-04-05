# src/schemas/quiz_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class QuizOption(BaseModel):
    text: str = Field(..., description="The answer text. FORMATTING RULES: 1. If the answer is just words/text, write normally WITHOUT delimiters. 2. If the answer is a number, equation, or symbol, wrap it in standard LaTeX delimiters \\( and \\). 3. Mixed: 'El valor es \\( 5 \\)'. CRITICAL: Do NOT include meta-words like 'Failure Path'.")
    feedback: str = Field(..., description="Short feedback explaining why this option is right/wrong to the student. Speak directly to the student. Do NOT use meta-words like 'Failure Path' or 'Trap'.")

class QuizQuestion(BaseModel):
    question_title: str = Field(..., description="Title with number, e.g., '# 1. Topic'")
    
    # -------------------------------------------------------------------------
    # 1. VISUAL-FIRST ANCHORING: Decide the visual BEFORE the logic
    # -------------------------------------------------------------------------
    plot_prompt: Optional[str] = Field(
        None, 
        description=(
            "Mathematical instructions for Matplotlib. "
            "The generated graph must contain the critical data needed to solve the problem. "
            "Leave null if no data visual is required."
        )
    )

    image_prompt: Optional[str] = Field(
        None, 
        description=(
            "Instructions for a creative, decorative illustration. "
            "CRITICAL: You MUST use natural, realistic metaphors suitable for classic Impressionist art (e.g., landscapes, nature, gardens, or 19th-century everyday physical scenes) to represent abstract concepts. "
            "Translate the core concept into an implicit, real-world physical scene. "
            "Leave null if no creative visual is required."
        )
    )

    # -------------------------------------------------------------------------
    # 2. CONTEXT-FIRST ANCHORING (Foundational Texts)
    # -------------------------------------------------------------------------
    context_text: Optional[str] = Field(
        None, 
        description=(
            "The foundational reading passage or shared scenario. "
            "Provide the raw text directly without any introductory labels or prefixes. "
            "Leave null if no reading passage is required."
        )
    )

    source_url: Optional[str] = Field(
        None, 
        description="The exact URL of the web search. CRITICAL: If you did not perform a web search, you MUST leave this as null. Do NOT hallucinate or invent URLs."
    )

    # -------------------------------------------------------------------------
    # 3. LOGIC ENGINE: Preserved 'THE SETUP' + Anti-Echo Constraint
    # -------------------------------------------------------------------------
    explanation: str = Field(..., description=(
        "Internal reasoning plan structured as follows:\n"
        "1. THE SETUP: Define the exact facts or numbers to be used. If a visual or context exists, state 'Data derived from graph/context'.\n"
        "2. THE SOLUTION: A step-by-step derivation using only the setup. Explicitly state every logical or arithmetic step.\n"
        "3. THE TRAPS: Identify 3 distinct failure paths based on the setup.\n"
        "This field is for logic only; omit the final question text or options."
    ))

    # -------------------------------------------------------------------------
    # 4. STUDENT FACING TEXT
    # -------------------------------------------------------------------------
    question_text: str = Field(..., description=(
        "The student-facing question stem. "
        "Wrap math expressions, numbers, and symbols in standard LaTeX \\( and \\). "
        "If a plot_prompt is present, the text must refer to the graph and omit the "
        "specific data points required for the solution."
    ))
    
    image_url: Optional[str] = Field(None, description="URL of the generated image/graph. If you wrote an image_prompt or plot_prompt, LEAVE THIS NULL. The backend will populate it automatically.")

    difficulty: Literal[1, 2, 3] = Field(1, description="Difficulty weight: 1 (Basic/Easy), 2 (Application/Medium), 3 (Analysis/Hard).")

    options: List[QuizOption] = Field(..., description="Exactly 4 options.")
    correct_option_index: Literal[0, 1, 2, 3] = Field(..., description="Index of the correct option (0-3).")

class QuizResponse(BaseModel):
    title: str = Field(..., description="An engaging short title for the quiz. (max. 6 words)")
    intro_message: str = Field(..., description="A single sentence introduction to the quiz in the Roma persona.")
    question_count: int = Field(..., description="The total number of questions generated in this quiz.")
    questions: List[QuizQuestion]

    easier_payload: str = Field(..., description="A user command to request an easier version of this quiz.")
    harder_payload: str = Field(..., description="A user command to request a more advanced version of this quiz.")
    retry_payload: str = Field(..., description="A user command to request a new quiz on the same topics and difficulty.")