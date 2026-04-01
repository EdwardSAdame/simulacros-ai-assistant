# src/config/exam_frameworks.py

ICFES_GLOBAL = """## ACADEMIC FRAMEWORK: ICFES Saber 11
GLOBAL STRATEGY: Focus on competency-based evaluation and psychometric awareness.
DISTRACTOR LOGIC: The AI must craft and explain distractors that are factually true statements in the real world (e.g., a valid legal principle or a true biological fact) but are contextually irrelevant to the specific prompt. Always enforce the "most specific response" rule."""

ICFES_DOMAINS = {
    "matematicas": """### DOMAIN: MATHEMATICS (QUANTITATIVE REASONING)
- Overview: Evaluates generic (daily life citizen math) and non-generic (STEM-focused) competencies. Highly focused on data literacy and real-world application.
- Focus: Interpretation of abstract data, strategic problem-solving planning, and logical justification.
- Topics: Statistics & Probability (charts, variance, combinations/permutations, percentiles), Geometry (spatial modeling, transformations, Pythagorean applications), Algebra & Calculus (linear/quadratic/exponential functions, rates of change).
- Strategy: Present scenarios involving tables, charts, or economic data.""",

    "lectura_critica": """### DOMAIN: CRITICAL READING
- Overview: Hermeneutic comprehension evaluating both continuous texts (essays, novels, philosophy) and discontinuous texts (infographics, comics, data tables).
- Focus: Literal, Inferential, and Critical-Intertextual levels.
- Topics: Extracting local semantic elements, uncovering text macrostructures, deducing implicit premises, identifying formal/informal fallacies, and unmasking ideological biases.
- Strategy: Describe visual texts (infographics/comics) clearly if simulating discontinuous texts. Force the user to differentiate between the author's main thesis and secondary supporting data.""",

    "sociales_ciudadanas": """### DOMAIN: SOCIAL AND CITIZEN SCIENCES
- Overview: Integration of history, geography, economics, and constitutional citizenship. Evaluates the ability to map social problems systemically.
- Focus: Social thinking, perspective analysis, and systemic/reflective thinking.
- Topics: Colombian Constitution of 1991 (mechanisms of citizen participation, branches of power, state of rights), 20th/21st-century Colombian history (violence, peace agreements, socioeconomic shifts), and global economic impacts.
- Strategy: When analyzing perspectives, force the user to suspend their own moral/ethical judgment. The correct answer must strictly reflect the logical internal interest of the actor described in the prompt, regardless of ethical alignment.""",

    "ciencias_naturales": """### DOMAIN: NATURAL SCIENCES
- Overview: Applied phenomenological problem-solving combining Biology, Chemistry, Physics, and CTS (Science, Technology, and Society).
- Focus: Iconographic analysis and experimental design. The core data to solve the problem should often be embedded in described graphs, circuits, or diagrams rather than just the introductory text.
- Topics: Biology (cellular transport, central dogma/protein synthesis, mitosis vs meiosis, Mendelian genetics, ecology), Chemistry (periodic trends, bonding, stoichiometry, conservation of mass), Physics (kinematics, Newton's laws, thermodynamics, mechanical energy conservation).
- Strategy: Present experimental setups. Ask the user to validate hypotheses, identify controlled/dependent variables, or extrapolate conclusions from empirical data sets.""",

    "ingles": """### DOMAIN: ENGLISH
- Overview: Evaluates communicative, pragmatic, lexical, and grammatical competence aligned with the CEFR (levels A- to B1+).
- Focus: 7 distinct parts of progressive difficulty measuring specific cognitive-linguistic skills.
- Topics: Part 1 (Lexical matching), Part 2 (Pragmatic signs and physical locations), Part 3 (Conversational coherence), Part 4 (Basic grammar cloze), Part 5 (Literal reading comprehension), Part 6 (Inferential reading comprehension), Part 7 (Advanced lexico-grammatical cloze).
- Strategy: Clearly identify which of the 7 parts is being simulated. Provide culturally relevant contexts and test specific structural rules (e.g., modals, perfect tenses, conditionals)."""
}


UNAL_GLOBAL = """## ACADEMIC FRAMEWORK: Universidad Nacional de Colombia (UNAL) Admission Exam
GLOBAL STRATEGY: Focus on deep analytical rigor, advanced problem-solving, and psychometric awareness."""

UNAL_DOMAINS = {
    "analisis_textual": """### DOMAIN: TEXTUAL ANALYSIS
- Overview: Deep hermeneutic comprehension of referential texts (Science, Humanities) and poetic-literary texts.
- Focus: Penalize superficial reading. Heavily emphasize Inferential and Critical-Intertextual levels.
- Topics: Deducing hidden premises, differentiating strict semantic definitions, judging authorial ideological bias, distinguishing facts from opinions, and applying mathematical propositional logic to natural language statements.
- Strategy: Analyze syntax, semantics, and authorial intent. Deconstruct arguments logically to find underlying meanings.""",

    "matematicas": """### DOMAIN: MATHEMATICS
- Overview: Mathematical modeling and translating natural language into formal algebraic/geometric structures. Rote memorization of formulas is insufficient.
- Focus: Numerical, Spatial, Metric, Random, and Variational thinking.
- Topics: Number hierarchies, system of equations (geometric interpretation), quadratic discriminants, geometric optimization (areas/volumes), analytic geometry (conics, slopes), function transformations, parity (even/odd), trigonometric identities, combinatorics (permutations vs. combinations), and expected value.
- Strategy: Stimulate reflection through the interpretation of schemes.""",

    "ciencias_naturales": """### DOMAIN: NATURAL SCIENCES
- Overview: Interdisciplinary phenomenology combining macroscopic principles, atomic reactivity, and cellular metabolism within single experimental scenarios.
- Components: 
    - Physics: Galilean relativity, free-body diagrams, mechanical energy conservation, fluid dynamics (Archimedes, Bernoulli).
    - Chemistry: Periodic trends, Lewis structures, strict stoichiometry.
    - Biology: Cellular organelles, central dogma (transcription/translation), mitosis vs. meiosis, Mendelian genetics (Punnett squares), trophic network thermodynamics.
- Strategy: Prioritize the analysis of concepts and processes represented in schemas. Focus on synthesis, deduction, and the application of fundamental laws.""",

    "ciencias_sociales": """### DOMAIN: SOCIAL SCIENCES
- Overview: Structural analysis of historical causalities, geographical systems, and philosophical arguments.
- Components: 
    - History: Epistemic ruptures (Renaissance, Revolutions), Colombian constitutional evolution (1886 to 1991).
    - Geography: Astronomical dynamics, Colombian orography and thermal floors, global demographics.
    - Philosophy & Logic: Classical to Contemporary thought (Plato, Descartes, Kant, Marx, Nietzsche, Freud), formal propositional logic, syllogisms, and informal fallacies.
- Strategy: Analyze social phenomena through contextualized problems. Evaluate the ability to use social science codes to solve complex situational queries.""",

    "analisis_imagen": """### DOMAIN: IMAGE ANALYSIS
- Overview: Pure abstract logical reasoning, fluid intelligence, and visuospatial cognition.
- Focus: Mental rotation, deductive transformation, and comparative visual analytics.
- Topics: Orthogonal views and 3D isometry, unfolding flat templates with symbols into 3D solids, differentiating specular reflections (mirror effect) from planar rotations, dynamic origami (predicting unfolded cuts), and spatial logic sequences.
- Strategy: Explain visual transformations step-by-step (rotations, reflections). Explicitly describe the pattern recognition logic."""
}

GENERAL_FRAMEWORK = """## ACADEMIC FRAMEWORK: General University Preparation
GLOBAL STRATEGY: Build strong foundational knowledge across core academic subjects.

CRITICAL MISSION (EXAM DISCOVERY): 
The user has not yet specified which admission exam they are preparing for (e.g., ICFES Saber 11 or Universidad Nacional UNAL).
Strategy: Answer their immediate question clearly, but naturally ask them which specific exam or university they are targeting so you can tailor your future explanations, difficulty, and practice questions to that specific test."""

def get_exam_framework(exam_context: str, category: str = "general") -> str:
    """
    Returns the appropriate pedagogical framework based on the provided exam context and category.
    If category is 'general', returns the full exam framework.
    If category is specific, returns ONLY the relevant domain to save tokens and enforce focus.
    """
    if exam_context == "UNAL":
        if category == "general" or category not in UNAL_DOMAINS:
            return UNAL_GLOBAL + "\n\n" + "\n\n".join(UNAL_DOMAINS.values())
        else:
            return UNAL_GLOBAL + "\n\n" + UNAL_DOMAINS[category]
            
    elif exam_context == "ICFES":
        if category == "general" or category not in ICFES_DOMAINS:
            return ICFES_GLOBAL + "\n\n" + "\n\n".join(ICFES_DOMAINS.values())
        else:
            return ICFES_GLOBAL + "\n\n" + ICFES_DOMAINS[category]
            
    return GENERAL_FRAMEWORK.strip()