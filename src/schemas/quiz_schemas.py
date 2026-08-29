# FILE: src/schemas/quiz_schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

LATEX_INSTRUCTION = (
    " CRITICAL MATH FORMATTING: All mathematical expressions, variables, numbers, and equations MUST be formatted "
    "using escaped LaTeX delimiters. Use \\( and \\) for inline math. Use \\[ and \\] for display math. "
)

class ScaleConfig(BaseModel):
    min_score: float = Field(..., description="Minimum possible score on this standardized scale.")
    max_score: float = Field(..., description="Maximum possible score on this standardized scale.")
    mean: float = Field(..., description="Statistical mean of the standard normal distribution for this exam.")
    standard_deviation: float = Field(..., description="Standard deviation of the distribution for this exam.")

class EvaluationMetadata(BaseModel):
    exam_type: Literal["icfes", "unal"] = Field(..., description="The examination framework evaluated (icfes or unal).")
    evaluation_level: Literal["component", "global"] = Field(..., description="Whether this evaluates a single component or the global exam.")
    subject_category: str = Field(
        ..., 
        description="The properly capitalized and accented name of the specific academic subject being evaluated."
    )
    scale_config: ScaleConfig = Field(..., description="The mathematical scaling configuration for this exam.")

class PsychometricParams(BaseModel):
    a_discrimination: float = Field(
        ..., 
        description="Item discrimination (a-parameter). If exam_type is 'unal' (Rasch model), this MUST be exactly 1.0. If 'icfes' (3PL), use a realistic value typically between 0.5 and 2.5."
    )
    b_difficulty: float = Field(
        ..., 
        description="Item difficulty (b-parameter) on a logit scale. Typically ranges from -3.0 (very easy) to +3.0 (very hard)."
    )
    c_guessing: float = Field(
        ..., 
        description="Pseudo-guessing probability (c-parameter). If exam_type is 'unal' (Rasch model), this MUST be exactly 0.0. If 'icfes' (3PL), use a realistic value typically between 0.0 and 0.25."
    )

class QuizOption(BaseModel):
    feedback: str = Field(..., description=(
        "Short feedback explaining exactly why this specific option is right or wrong. "
        "By writing this first, you anchor the logical trap or solution this option represents. "
        "Speak directly to the student. DO NOT put the literal answer choice here." + LATEX_INSTRUCTION
    ))

    text: Optional[str] = Field(
        None, 
        description=(
            "The literal answer choice text that the student will select. "
            "CRITICAL KERNEL RULE: If the question format is `text_to_text` or `image_to_text`, this field MUST NOT BE NULL. "
            "STRICT MUTUAL EXCLUSIVITY: If you are populating `plot_prompt` for this option (formats `image_to_image` or `text_to_image`), this field MUST BE EXACTLY NULL. Do not provide both." + LATEX_INSTRUCTION
        )
    )
    
    plot_prompt: Optional[str] = Field(
        None, 
        description=(
            "A NATURAL LANGUAGE description of the graph needed for THIS SPECIFIC OPTION. "
            "STRICT MUTUAL EXCLUSIVITY: Leave exactly null if the question's `format_type` is `text_to_text` or `image_to_text`. If populated, the `text` field MUST be null."
        )
    )

    image_url: Optional[str] = Field(
        None, 
        description="URL of the generated option graph. If you wrote a plot_prompt, LEAVE THIS NULL."
    )

    original_index: Optional[int] = Field(
        None, 
        description="Internal field used by the backend to track the option's original position before shuffling."
    )

class QuizQuestion(BaseModel):
    question_title: str = Field(..., description="Title with question number, e.g., '# 1. Topic'.")
    
    format_type: Literal["text_to_text", "image_to_text", "text_to_image", "image_to_image"] = Field(
        ..., 
        description="The required structural layout for this individual question."
    )

    explanation: str = Field(..., description="Internal reasoning and structural blueprint. Write this before generating the question text." + LATEX_INSTRUCTION)

    context_text: Optional[str] = Field(
        None, 
        description=(
            "Optional question-specific setup or formula premise. "
            "CRITICAL RULE: For shared reading passages, do NOT place the passage here. "
            "Place it in the parent QuestionGroup's context_text field instead." + LATEX_INSTRUCTION
        )
    )

    source_url: Optional[str] = Field(
        None, 
        description="The exact URL of the web search. Leave null if no search was performed."
    )

    question_text: str = Field(..., description="The specific interrogative sentence or direct command." + LATEX_INSTRUCTION)

    plot_prompt: Optional[str] = Field(
        None, 
        description="A NATURAL LANGUAGE description of the data or math graph needed for the main question stem."
    )

    image_prompt: Optional[str] = Field(
        None, 
        description="A purely artistic and atmospheric representation of a physical environment for this specific question."
    )
    
    image_url: Optional[str] = Field(
        None, 
        description="URL of the generated image/graph for the question stem. LEAVE THIS NULL if you wrote a prompt."
    )

    difficulty_label: Literal[1, 2, 3] = Field(1, description="Difficulty weight indicator: 1 (Easy), 2 (Medium), 3 (Hard).")

    correct_option_index: Literal[0, 1, 2, 3] = Field(..., description="Index of the correct option (0-3).")

    options: List[QuizOption] = Field(..., description="Exactly 4 options.")

    psychometric_params: PsychometricParams = Field(..., description="Item Response Theory parameters.")

class QuestionGroup(BaseModel):
    group_title: Optional[str] = Field(
        None, 
        description="Optional short title for the shared reading passage or stimulus block."
    )
    
    context_text: Optional[str] = Field(
        None, 
        description=(
            "The shared reading passage, case study, dataset, or stimulus text for this group of questions. "
            "For standalone 1-on-1 questions without a shared reading passage, leave this field as null." + LATEX_INSTRUCTION
        )
    )

    group_source_url: Optional[str] = Field(
        None,
        description="The exact URL or citation source for the shared reading passage. Leave null if no source is needed."
    )

    group_plot_prompt: Optional[str] = Field(
        None,
        description=(
            "A NATURAL LANGUAGE description of a shared data or math graph needed for the ENTIRE group context. "
            "Leave null if the group context does not require an analytical graph, or if this is a standalone question."
        )
    )

    group_image_prompt: Optional[str] = Field(
        None,
        description=(
            "A purely artistic and atmospheric representation for the shared reading passage or group context. "
            "Leave null if the group context does not require a decorative image, or if this is a standalone question."
        )
    )

    group_image_url: Optional[str] = Field(
        None,
        description="URL of the generated image/graph for the group context. LEAVE THIS NULL if you wrote a prompt."
    )
    
    questions: List[QuizQuestion] = Field(
        ..., 
        description="List of 1 to 5 questions associated with this shared context passage or standalone group."
    )

class QuizResponse(BaseModel):
    title: str = Field(..., description="An engaging short title for the quiz.")
    intro_message: str = Field(..., description="A single sentence introduction to the quiz in the persona.")
    question_count: int = Field(..., description="The total number of questions generated across all groups.")
    
    evaluation_metadata: EvaluationMetadata = Field(..., description="Mathematical and contextual metadata.")
    
    groups: List[QuestionGroup] = Field(..., description="List of question groups.")

    easier_payload: str = Field(..., description="A user command to request an easier version of this quiz.")
    harder_payload: str = Field(..., description="A user command to request a more advanced version of this quiz.")
    retry_payload: str = Field(..., description="A user command to request a new quiz on the same topics.")