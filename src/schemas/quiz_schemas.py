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
            "DATA VISUALS ONLY. Use this exclusively for math, statistics, physics, geometry, charts, and graphs. "
            "Provide pure mathematical instructions for Matplotlib. "
            "CRITICAL VISUAL DEPENDENCY: If you use this field, the graph MUST contain the critical data needed to solve the problem. Do NOT put the solving data in the question_text. "
            "STRICT NULL RULE: If this question does NOT require a data visual, you MUST return a literal JSON null."
        )
    )

    image_prompt: Optional[str] = Field(
        None, 
        description=(
            "CREATIVE VISUALS ONLY. Use this exclusively for historical scenes, literary contexts, or biological illustrations. "
            "CRITICAL EXCLUSION: NEVER put charts, graphs, or math in this field. "
            "STRICT NULL RULE: If this question does NOT require a creative visual, you MUST return a literal JSON null."
        )
    )

    # -------------------------------------------------------------------------
    # 2. CONTEXT-FIRST ANCHORING (Foundational Texts)
    # -------------------------------------------------------------------------
    context_text: Optional[str] = Field(
        None, 
        description=(
            "The full reading passage or foundational data. "
            "CRITICAL RULE: If this question requires a text to read, WRITE THE ACTUAL TEXT HERE. "
            "Do NOT hide the reading passage in the explanation. Leave null ONLY if no context_text is needed."
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
        "Detailed reasoning plan. YOU MUST FOLLOW THIS STRUCTURE:\n"
        "1. THE SETUP: Define the EXACT numbers/facts you will use. If you wrote a plot_prompt or context_text, state 'Data derived from graph/context'. DO NOT draft the reading passage here.\n"
        "2. THE SOLUTION: Solve the problem step-by-step using ONLY the setup. You must write out every single arithmetic operation explicitly.\n"
        "3. THE TRAPS: Identify 3 failure paths based on these specifics.\n"
        "CRITICAL RULE: DO NOT draft, echo, or repeat the question text or options here."
    ))

    # -------------------------------------------------------------------------
    # 4. STUDENT FACING TEXT
    # -------------------------------------------------------------------------
    question_text: str = Field(..., description="The student-facing question stem. FORMATTING: Wrap ONLY math expressions, numbers, and symbols in standard LaTeX (\\( and \\)). CRITICAL VISUAL RULE: If this question has a plot_prompt or image_prompt, this text MUST refer to it (e.g., 'De acuerdo con la gráfica...') and MUST NOT reveal the exact numbers needed to solve the problem. CRITICAL ANTI-LEAK: NEVER include internal meta-labels like 'Core Constraints'.")
    
    image_url: Optional[str] = Field(None, description="URL of the generated image/graph. If you wrote an image_prompt or plot_prompt, LEAVE THIS NULL. The backend will populate it automatically.")

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