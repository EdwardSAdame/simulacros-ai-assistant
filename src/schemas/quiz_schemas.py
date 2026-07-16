# src/schemas/quiz_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class QuizOption(BaseModel):
    # -------------------------------------------------------------------------
    # 1. OPTION REASONING (Chain of Thought first)
    # -------------------------------------------------------------------------
    feedback: str = Field(..., description=(
        "Short feedback explaining exactly why this specific option is right or wrong. "
        "By writing this first, you anchor the logical trap or solution this option represents. "
        "Speak directly to the student. DO NOT put the literal answer choice here; this field is exclusively for the explanation."
    ))

    # -------------------------------------------------------------------------
    # 2. OPTION EXECUTION (Text or Visual)
    # -------------------------------------------------------------------------
    text: Optional[str] = Field(
        None, 
        description=(
            "The literal answer choice text that the student will select. "
            "CRITICAL KERNEL RULE: If the question format is `text_to_text` or `image_to_text`, this field MUST NOT BE NULL. "
            "You must write the actual answer here. "
            "Only leave this as a literal JSON null if you are writing a `plot_prompt` for this specific option. "
            "FORMATTING RULES: "
            "1. If the answer is just words/text, write normally WITHOUT delimiters. "
            "2. If the answer is a number, equation, or symbol, wrap it in standard LaTeX delimiters \\( and \\)."
        )
    )
    
    plot_prompt: Optional[str] = Field(
        None, 
        description=(
            "A NATURAL LANGUAGE description of the graph needed for THIS SPECIFIC OPTION. "
            "CRITICAL KERNEL RULE: ONLY write descriptive natural language. "
            "Leave null if the question's `format_type` is `text_to_text` or `image_to_text`."
        )
    )

    image_url: Optional[str] = Field(
        None, 
        description="URL of the generated option graph. If you wrote a plot_prompt, LEAVE THIS NULL. The backend will populate it automatically."
    )

    original_index: Optional[int] = Field(
        None, 
        description="Internal field used by the backend to track the option's original position before shuffling."
    )


class QuizQuestion(BaseModel):
    question_title: str = Field(..., description=(
        "Title with question number, e.g., '# 1. Topic'. "
        "CRITICAL KERNEL RULE: You MUST NOT include any structural metadata, layout notes, or format types "
        "such as '(imagen a imagen)', '(imagen a texto)', '(texto)', or similar descriptive suffixes. "
    ))
    
    # -------------------------------------------------------------------------
    # STEP 1: THE ARCHITECTURAL ANCHOR
    # -------------------------------------------------------------------------
    format_type: Literal["text_to_text", "image_to_text", "text_to_image", "image_to_image"] = Field(
        ..., 
        description=(
            "CRITICAL: The required structural layout for this question as mandated by the system prompt. "
            "You MUST select the exact format assigned to this question number in the instructions. "
            "This dictates whether you will write natural language plot descriptions in the stem, the options, both, or neither."
        )
    )

    # -------------------------------------------------------------------------
    # STEP 2: THE MASTER REASONING BLOCK (Plan before executing)
    # -------------------------------------------------------------------------
    explanation: str = Field(..., description=(
        "Internal reasoning and structural blueprint. You MUST write this before generating the question text or visuals.\n"
        "1. THE SCENARIO: Define the exact facts, numbers, or geometric properties.\n"
        "2. THE VISUAL MAPPING: Based on the `format_type` above, explicitly state if the stem needs a `plot_prompt` and if the options need `plot_prompt`s.\n"
        "3. THE SOLUTION: The step-by-step arithmetic, logical derivation, or visual transformation to reach the correct answer.\n"
        "4. THE TRAPS: Identify 3 plausible calculation/visual errors to use as distractors.\n"
        "This field is for internal logic only; omit final question text."
    ))

    # -------------------------------------------------------------------------
    # STEP 3: CONTEXT & QUESTION STEM EXECUTION
    # -------------------------------------------------------------------------
    context_text: Optional[str] = Field(
        None, 
        description=(
            "The foundational premise, background information, or scenario setup. This establishes the facts of the problem. "
            "CRITICAL RULE: DO NOT include the actual interrogative question or task here. "
            "NEVER use this to describe data that should be rendered visually via a `plot_prompt`. "
            "For reading comprehension or creative subjects using `image_to_text`, this field MUST contain the complete reading passage or text stimulus required to answer the question."
        )
    )

    source_url: Optional[str] = Field(
        None, 
        description="The exact URL of the web search. Leave null if no search was performed."
    )

    question_text: str = Field(..., description=(
        "The specific interrogative sentence or direct command. "
        "CRITICAL KERNEL RULE: DO NOT repeat any of the background facts or scenario details already provided in context_text. "
        "This field must ONLY contain the final question being asked. "
        "NO META-LABELS. Wrap math in \\( \\). "
        "If a `plot_prompt` is provided, the text should introduce the data shown in the graph naturally. "
        "DO NOT inject, list, or append the answer choices into this field under any circumstances."
    ))

    plot_prompt: Optional[str] = Field(
        None, 
        description=(
            "A NATURAL LANGUAGE description of the data or math graph needed for the main question stem. "
            "CRITICAL KERNEL RULE: You MUST NOT write Python or Matplotlib code here. ONLY write descriptive natural language. "
            "Leave null if `format_type` is `text_to_text` or `text_to_image`."
        )
    )

    image_prompt: Optional[str] = Field(
        None, 
        description=(
            "A purely artistic and atmospheric representation of a physical environment. "
            "Focus exclusively on natural landscapes or tangible real-world scenes. No academic tropes. "
            "CRITICAL RULE: This image is strictly ornamental. It MUST NOT contain any text, reading passages, or data required to solve the question. "
            "Leave null if `format_type` is `text_to_text` or `text_to_image`."
        )
    )
    
    image_url: Optional[str] = Field(
        None, 
        description="URL of the generated image/graph for the question stem. LEAVE THIS NULL if you wrote a prompt."
    )

    difficulty: Literal[1, 2, 3] = Field(1, description="Difficulty weight: 1 (Easy), 2 (Medium), 3 (Hard).")

    # -------------------------------------------------------------------------
    # STEP 4: DECISION & OPTIONS EXECUTION
    # -------------------------------------------------------------------------
    correct_option_index: Literal[0, 1, 2, 3] = Field(
        ..., 
        description="Index of the correct option (0-3). Decide this before generating the options array."
    )

    options: List[QuizOption] = Field(..., description="Exactly 4 options, executing the traps and solution planned in the explanation.")


class QuizResponse(BaseModel):
    title: str = Field(..., description="An engaging short title for the quiz. (max. 6 words)")
    intro_message: str = Field(..., description="A single sentence introduction to the quiz in the Roma persona.")
    question_count: int = Field(..., description="The total number of questions generated in this quiz.")
    questions: List[QuizQuestion]

    easier_payload: str = Field(..., description="A user command to request an easier version of this quiz.")
    harder_payload: str = Field(..., description="A user command to request a more advanced version of this quiz.")
    retry_payload: str = Field(..., description="A user command to request a new quiz on the same topics and difficulty.")