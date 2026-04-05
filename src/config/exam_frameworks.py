# src/config/exam_frameworks.py

ICFES_GLOBAL = """## ACADEMIC FRAMEWORK: ICFES Saber 11
GLOBAL STRATEGY: Focus on competency-based evaluation and psychometric awareness.
DISTRACTOR LOGIC: You must craft and explain distractors that are factually true statements in the real world but are contextually irrelevant to the specific prompt.

SCORE INTERPRETATION RULES:
- Method: Scored using Item Response Theory (IRT 3PL). Scores depend on item difficulty, discrimination, and guessing parameters.
- Components: Scaled from 0 to 100. The theoretical mean is 50 and the standard deviation is 10.
- Global Score: Ranges from 0 to 500, with a theoretical mean of 250. It uses a weighted formula: English weighs 1; Math, Reading, Social Studies, and Natural Sciences weigh 3 each.
- Percentiles: Ranges from 0 to 100, indicating the exact relative national position."""

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
GLOBAL STRATEGY: Focus on deep analytical rigor, advanced problem-solving, and psychometric awareness.

SCORE INTERPRETATION RULES:
- Method: The exam is scored using the Rasch Model (Item Response Theory). Scores depend on the calibrated difficulty of the questions answered correctly.
- Components: Standardized to a Mean of 10 and Standard Deviation of 1. A score of 10 is strictly average.
- Total Score: Ranges theoretically from ~200 to ~1000, with a strict Mean of 500 and Standard Deviation of 100."""

UNAL_DOMAINS = {
    "analisis_textual": """### DOMAIN: TEXTUAL ANALYSIS
- Overview: Deep hermeneutic comprehension of referential texts (Science, Humanities) and poetic-literary texts.
- Focus: Penalize superficial reading. Heavily emphasize Inferential and Critical-Intertextual levels.
- Topics: Deducing hidden premises, differentiating strict semantic definitions, judging authorial ideological bias, distinguishing facts from opinions, and applying mathematical propositional logic to natural language statements.
- Strategy: Analyze syntax, semantics, and authorial intent. Deconstruct arguments logically to find underlying meanings.""",

    "matematicas": """### DOMAIN: MATHEMATICS
- Overview: Mathematical modeling and translating natural language into formal algebraic/geometric structures. Rote memorization of formulas is insufficient.
- Focus: Numerical, Spatial, Metric, Random, and Variational thinking.
- Topics: numerical sets, arithmetic 1, arithmetic 2, arithmetic 3, sequences, algebra 1, algebra 2, functions, graphing functions, geometry 1, geometry 2, trigonometry 1, trigonometry 2, statistics and probability, analytic geometry, calculus.
- Strategy: Stimulate reflection through the interpretation of schemes.""",

    "ciencias_naturales": """### DOMAIN: NATURAL SCIENCES
- Overview: Interdisciplinary phenomenology combining macroscopic principles, atomic reactivity, and cellular metabolism within single experimental scenarios.
- Components: 
    - Physics: Galilean relativity, free-body diagrams, mechanical energy conservation, fluid dynamics (Archimedes, Bernoulli), measurements, kinematics, dynamics, work, energy, momentum, gravitation, electricity and magnetism, fluid mechanics, thermodynamics, oscillatory motion and waves, optics.
    - Chemistry: matter, atomic chemistry, inorganic chemistry, stoichiometry, solutions, organic chemistry, gases, electrochemistry and chemical kinetics.
    - Biology: biomolecules, substance transport, protein synthesis, cell cycle, cell division, Mendelian genetics, population genetics, metabolism, metabolic pathways for energy production, photosynthesis, circulation and respiration, reproduction, ecology, evolution.
    - Strategy: Prioritize the analysis of concepts and processes represented in schemas. Focus on synthesis, deduction, and the application of fundamental laws.""",

    "ciencias_sociales": """### DOMAIN: SOCIAL SCIENCES
- Overview: Structural analysis of historical causalities, geographical systems, and philosophical arguments.
- Components: 
    - History: Epistemic ruptures, Colombian constitutional evolution (1886 to 1991), world history 1, world history 2, history of the Americas, Colombian history 1, Colombian history 2.
    - Geography: Astronomical dynamics, Colombian orography and thermal floors, global demographics, geography 1, geography 2.
    - Philosophy & Logic: Classical to Contemporary thought (Plato, Descartes, Kant, Marx, Nietzsche, Freud), formal propositional logic, syllogisms, and informal fallacies.
    - Economics: General economy.
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

def get_exam_framework(exam_context: str, category: str = "general", intent: str = "chat") -> str:
    """
    Returns the appropriate pedagogical framework based on exam context, category, and intent.
    - If intent is 'chat', returns ONLY the Global Strategy (saves tokens).
    - If intent is 'quiz' and category is 'general', returns Global Strategy + ALL domains.
    - If intent is 'quiz' and category is specific, returns Global Strategy + SPECIFIC domain.
    """
    if exam_context == "UNAL":
        # If the user is just chatting, save tokens and only inject the core global rules
        if intent != "quiz":
            return UNAL_GLOBAL
            
        # If they want a quiz, determine if it's general or subject-specific
        if category == "general" or category not in UNAL_DOMAINS:
            return UNAL_GLOBAL + "\n\n" + "\n\n".join(UNAL_DOMAINS.values())
        else:
            return UNAL_GLOBAL + "\n\n" + UNAL_DOMAINS[category]
            
    elif exam_context == "ICFES":
        # If the user is just chatting, save tokens and only inject the core global rules
        if intent != "quiz":
            return ICFES_GLOBAL
            
        # If they want a quiz, determine if it's general or subject-specific
        if category == "general" or category not in ICFES_DOMAINS:
            return ICFES_GLOBAL + "\n\n" + "\n\n".join(ICFES_DOMAINS.values())
        else:
            return ICFES_GLOBAL + "\n\n" + ICFES_DOMAINS[category]
            
    return GENERAL_FRAMEWORK.strip()