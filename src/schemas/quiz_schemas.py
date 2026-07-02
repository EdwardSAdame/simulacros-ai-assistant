# src/schemas/quiz_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class QuizOption(BaseModel):
    # -------------------------------------------------------------------------
    # OPTION TEXT & VISUALS (PATH 2: MODULAR OPTIONS)
    # -------------------------------------------------------------------------
    text: Optional[str] = Field(
        None, 
        description=(
            "The answer text. FORMATTING RULES: "
            "1. If the answer is just words/text, write normally WITHOUT delimiters. "
            "2. If the answer is a number, equation, or symbol, wrap it in standard LaTeX delimiters \\( and \\). "
            "CRITICAL: If you generate a `plot_prompt` for this option, you MUST leave this text field as a literal JSON null. "
            "Do NOT write 'Option A' or redundant equations if a visual is present."
        )
    )
    
    plot_prompt: Optional[str] = Field(
        None, 
        description=(
            "Mathematical instructions for Matplotlib to generate a graph for THIS SPECIFIC OPTION. "
            "Leave null unless the system instruction explicitly forces you to generate visual options."
        )
    )

    image_url: Optional[str] = Field(
        None, 
        description="URL of the generated option graph. If you wrote a plot_prompt, LEAVE THIS NULL. The backend will populate it automatically."
    )

    feedback: str = Field(..., description=(
        "Short feedback explaining why this option is right/wrong to the student. Speak directly to the student. "
        "Do NOT use meta-words like 'Failure Path' or 'Trap'."
    ))

    original_index: Optional[int] = Field(
        None, 
        description="Internal field used by the backend to track the option's original position before shuffling."
    )


class QuizQuestion(BaseModel):
    question_title: str = Field(..., description="Title with number, e.g., '# 1. Topic'")
    
    # -------------------------------------------------------------------------
    # 1. VISUAL-FIRST ANCHORING: Decide the visual BEFORE the logic
    # -------------------------------------------------------------------------
    plot_prompt: Optional[str] = Field(
        None, 
        description=(
            "Mathematical instructions for Matplotlib for the main question stem. "
            "The generated graph must contain the critical data needed to solve the problem. "
            "Leave null if no data visual is required for the stem."
        )
    )

    visual_metaphor_planning: Optional[str] = Field(
        None,
        description=(
            "INTERNAL THINKING STEP. Identify the broad, general subject of the question. "
            "Brainstorm a generic, static, real-world physical scene that fits this subject. "
            "Ignore the specific logic, variables, or data of the question. Focus EXCLUSIVELY on setting a beautiful, unrelated background mood."
        )
    )

    image_prompt: Optional[str] = Field(
        None, 
        description=(
            "The final illustration instructions based on your `visual_metaphor_planning`. "
            "Describe a generic, atmospheric physical scene in the requested art style. "
            "Keep this extremely concise. Focus only on the physical setting, lighting, and mood. "
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
            "CRITICAL RULES: "
            "1. Use ONLY for long reading comprehension texts or massive science experiment descriptions. "
            "2. Do NOT use this for standard math word problems or short setups. "
            "3. Do NOT put the actual interrogative question here. "
            "If the setup is less than 3 sentences, leave this NULL and put everything inside `question_text`."
        )
    )

    source_url: Optional[str] = Field(
        None, 
        description="The exact URL of the web search. CRITICAL: If you did not perform a web search, you MUST leave this as null. Do NOT hallucinate or invent URLs."
    )

    # -------------------------------------------------------------------------
    # 3. LOGIC ENGINE: DUAL-TRACK CHAIN OF THOUGHT
    # -------------------------------------------------------------------------
    explanation: str = Field(..., description=(
        "Internal reasoning plan structured based on the active Engine:\n"
        "FOR ENGINE 1 (TEXT OPTIONS - Math/Logic):\n"
        "1. THE SETUP: Define exact facts or numbers.\n"
        "2. THE SOLUTION: Step-by-step arithmetic or logical derivation.\n"
        "3. THE TRAPS: Identify 3 calculation or logic errors.\n\n"
        "FOR ENGINE 2 (IMAGE OPTIONS - Pure Visual Reasoning):\n"
        "1. THE VISUAL BASELINE: Define the initial visual state, data representation, or geometric structure in the STEM.\n"
        "2. THE VISUAL INFERENCE: Define the logical visual jump required (e.g., translating data to a new format, applying a spatial rule, or recognizing a structural pattern). DO NOT solve algebraically to find a single numeric coordinate.\n"
        "3. THE VISUAL TRAPS: Identify 3 plausible but visually flawed representations (e.g., incorrect axis mapping, inverted trends, distorted proportions).\n\n"
        "This field is for internal logic only; omit final question text."
    ))

    # -------------------------------------------------------------------------
    # 4. STUDENT FACING TEXT
    # -------------------------------------------------------------------------
    question_text: str = Field(..., description=(
        "The complete student-facing question. "
        "CRITICAL: For short word problems, put the ENTIRE scenario/setup AND the interrogative question here. Do not split it with `context_text`. "
        "STRICT FORMATTING RULE: Write as a fluid paragraph. Do NOT use Markdown headers, bold labels, or structural tags like '## Estímulo', '## Pregunta', 'Contexto:', or 'Pregunta:'. Just write the text naturally. "
        "Wrap math expressions, numbers, and symbols in standard LaTeX \\( and \\). "
        "If a `plot_prompt` is present, the text must refer to the graph. "
        "If an `image_prompt` is present, the image is strictly DECORATIVE. You MUST NOT refer to the image or 'estímulo visual' in this text."
    ))
    
    image_url: Optional[str] = Field(None, description="URL of the generated image/graph for the question stem. If you wrote an image_prompt or plot_prompt, LEAVE THIS NULL. The backend will populate it automatically.")

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