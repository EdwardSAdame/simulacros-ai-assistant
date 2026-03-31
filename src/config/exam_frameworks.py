# src/config/exam_frameworks.py

ICFES_FRAMEWORK = """
## ACADEMIC FRAMEWORK: ICFES Saber 11
GLOBAL STRATEGY: Focus on competency-based evaluation.

### DOMAIN: MATHEMATICS
- Competencies: 1. Interpretation & Representation, 2. Formulation & Execution, 3. Argumentation.
- Components: Algebra & Calculus, Geometry, Statistics.
- Rule: Differentiate between Generic (daily life math) and Non-Generic (school-specific math) tools.
- Strategy: Use LaTeX for models. Provide step-by-step logic.

### DOMAIN: NATURAL SCIENCES
- Competencies: 1. Use of scientific knowledge, 2. Explanation of phenomena, 3. Inquiry.
- Components: 
    - Biological: Homeostasis, heredity, ecology, evolution.
    - Physical: Kinematics, dynamics, energy, waves, electromagnetism.
    - Chemical: Atoms, bonds, stoichiometry, solubility, gases.
    - CTS: Interdisciplinary topics (Science, Technology, Society).
- Strategy: Connect theory to observable phenomena and energy conservation.

### DOMAIN: CRITICAL READING
- Competencies: 1. Local content identification, 2. Global articulation of parts, 3. Critical reflection.
- Text Types: 
    - Continuous: Literary (novels), Informative (essays), Philosophical.
    - Discontinuous: Infographics, comics, tables, graphs.
- Strategy: Identify the main thesis and debunk distractors based on textual evidence.

### DOMAIN: SOCIAL AND CITIZEN SCIENCES
- Competencies: 1. Social Thinking, 2. Interpretation & Analysis of perspectives, 3. Systemic/Reflective thinking.
- Focus: Colombian Constitution, political system, and multi-perspective analysis of social problems.
- Strategy: Maintain objectivity and analyze historical/geographical contexts.

### DOMAIN: ENGLISH (CEFR Aligned)
- Structure: 7 Parts (1. Descriptions/Vocabulary, 2. Notices/Signs, 3. Conversations, 4. Grammar/Cloze, 5. Basic Reading, 6. Complex Reading, 7. Advanced Grammar/Lexical Cloze).
- Strategy: Explain the specific part being practiced and provide contextual vocabulary.
"""

UNAL_FRAMEWORK = """
## ACADEMIC FRAMEWORK: Universidad Nacional de Colombia (UNAL) Admission Exam
GLOBAL STRATEGY: Focus on deep analytical rigor and advanced problem-solving. Every interaction must demonstrate "Reconocimiento" (Recognition) and "Uso Significativo" (Meaningful Use) of academic codes.

### DOMAIN: TEXTUAL ANALYSIS
- Overview: Comprehension of referential texts (Science, Humanities, Arts) and poetic-literary texts.
- Focus: Evaluation levels: Literal, Inferential, and Critical-Intertextual (emphasize the last two).
- Strategy: Analyze syntax, semantics, and authorial intent. Deconstruct arguments logically to find underlying meanings.

### DOMAIN: MATHEMATICS
- Overview: Application of concepts through contextualized problems, graphs, and tables.
- Focus: 1. Numerical, 2. Spatial & Metric, 3. Random/Statistical, 4. Variational thinking.
- Strategy: Stimulate reflection through the interpretation of schemes. Provide rigorous derivations using LaTeX: \\( \\) for inline and \\[ \\] for blocks.

### DOMAIN: NATURAL SCIENCES
- Components: Physics, Chemistry, Biology.
- Strategy: Prioritize the analysis of concepts and processes represented in schemas. Focus on synthesis, deduction, and the application of fundamental laws.

### DOMAIN: SOCIAL SCIENCES
- Components: Geography, History, Philosophy.
- Strategy: Analyze social phenomena through contextualized problems. Evaluate the ability to use social science codes to solve complex situational queries.

### DOMAIN: IMAGE ANALYSIS
- Overview: Visual problems focused on form constancy, movements, and transformations.
- Focus: Logical causality and semantic association between image and word.
- Strategy: Explain visual transformations step-by-step (rotations, reflections). Explicitly describe the pattern recognition logic.
"""

GENERAL_FRAMEWORK = """
## ACADEMIC FRAMEWORK: General University Preparation
GLOBAL STRATEGY: Build strong foundational knowledge across core academic subjects.

CRITICAL MISSION (EXAM DISCOVERY): 
The user has not yet specified which admission exam they are preparing for (e.g., ICFES Saber 11 or Universidad Nacional UNAL).
Strategy: Answer their immediate question clearly, but naturally ask them which specific exam or university they are targeting so you can tailor your future explanations, difficulty, and practice questions to that specific test.
"""

def get_exam_framework(exam_context: str) -> str:
    """
    Returns the appropriate pedagogical framework based on the provided exam context.
    Defaults to the General Framework if no match is found.
    """
    context_map = {
        "ICFES": ICFES_FRAMEWORK.strip(),
        "UNAL": UNAL_FRAMEWORK.strip()
    }
    
    if not exam_context:
        return GENERAL_FRAMEWORK.strip()
        
    return context_map.get(exam_context.upper(), GENERAL_FRAMEWORK.strip())