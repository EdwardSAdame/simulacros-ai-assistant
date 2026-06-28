# src/config/exam_frameworks.py

ICFES_GLOBAL = """## ACADEMIC FRAMEWORK: ICFES Saber 11
GLOBAL STRATEGY: Evidence-Centered Design. The exam evaluates competencies applied to real-world scenarios. Do not test rote memorization of isolated facts. Provide the necessary data within texts, graphs, or tables, and force the user to interpret, deduce, and argue based solely on the provided stimulus.

PSYCHOMETRIC MODEL & SCORE INTERPRETATION:
- Method: Item Response Theory (IRT 3PL). Questions must vary in difficulty, discrimination, and guessing probability.
- Distractor Logic: Distractors MUST NOT be obvious falsehoods. They must be factually true statements in the real world that fail to answer the specific prompt, or they must reflect common cognitive misinterpretations of the provided data.
- Components: Each domain is scaled 0 to 100 (Mean = 50, SD = 10).

MANDATORY BEHAVIOR: Always frame questions with a stimulus (a short text, an experimental design, a social scenario, or a dataset)."""

ICFES_DOMAINS = {
    "matematicas": """### DOMAIN: MATHEMATICS (QUANTITATIVE REASONING)
- Overview: Evaluates quantitative reasoning applied to daily life, citizenship, and basic STEM problems. 
- Competencies: Interpretation and Representation (34%), Formulation and Execution, Argumentation.
- Focus: Avoid pure abstract algebra. Focus heavily on data literacy, statistics, financial math, and applied geometry.
- Topics: Probabilities, interpreting complex statistical charts, variance, percentiles, spatial transformations, rates of change.
- Strategy: Present a scenario with a table or graph. Ask the user to evaluate the validity of a conclusion drawn from the data or calculate a required metric based on the provided parameters.""",

    "lectura_critica": """### DOMAIN: CRITICAL READING
- Overview: Hermeneutic comprehension evaluating continuous texts (essays, philosophical excerpts, literature) and discontinuous texts (infographics, comics, tables).
- Competencies: Local meaning (25%), global articulation (42%), critical reflection (33%).
- Focus: Deducing implicit premises, uncovering structural semantics, identifying authorial bias, and evaluating argument validity.
- Strategy: Present a text. Ask the user to identify the macrostructure, differentiate the main thesis from secondary evidence, or infer the underlying assumptions of the author.""",

    "sociales_ciudadanas": """### DOMAIN: SOCIAL AND CITIZEN SCIENCES
- Overview: Evaluates systemic social thinking, historical understanding, and constitutional citizenship.
- Competencies: Social thinking, Interpretation of perspectives, Systemic and reflective thinking.
- Topics: 1991 Colombian Constitution (mechanisms of participation, rights), 20th/21st-century Colombian conflicts, global economic geography.
- Strategy: Present a complex social conflict involving multiple stakeholders. Require the user to analyze the perspectives without applying personal ethical judgment. The correct answer must objectively reflect the logical interest of a specific actor.""",

    "ciencias_naturales": """### DOMAIN: NATURAL SCIENCES
- Overview: Evaluates applied phenomenological reasoning across Biology, Chemistry, Physics, and Science/Technology/Society (STS).
- Competencies: Use of scientific knowledge, Explanation of phenomena, Inquiry.
- Focus: Experimental design, hypothesis validation, reading scientific models. Rote formulas are less important than understanding physical/chemical laws conceptually.
- Strategy: Describe a laboratory setup or a natural phenomenon. Ask the user to identify controlled variables, deduce outcomes if a parameter changes, or explain the phenomenon using the data provided in the prompt.""",

    "ingles": """### DOMAIN: ENGLISH
- Overview: Evaluates communicative competence mapped strictly to the CEFR scale (A- to B1+).
- Focus: You must strictly simulate one of the 7 official parts of the ICFES English exam.
- The 7 Parts:
  - Part 1 (11%): Lexical matching (Given 5 descriptions, match to a list of words).
  - Part 2 (11%): Pragmatic signs (Where would you see this notice?).
  - Part 3 (11%): Communicative coherence (Choose the best response to a short dialogue).
  - Part 4 (18%): Basic grammar cloze (Fill in the blanks with basic structural grammar).
  - Part 5 (16%): Literal reading comprehension (Basic text).
  - Part 6 (11%): Inferential reading comprehension (Complex text, author's intent).
  - Part 7 (22%): Advanced lexico-grammatical cloze (Vocabulary in context).
- Strategy: State explicitly which of the 7 parts is being simulated. Adhere strictly to the format of that part."""
}

UNAL_GLOBAL = """## ACADEMIC FRAMEWORK: Universidad Nacional de Colombia (UNAL) Admission Exam
GLOBAL STRATEGY: Focus on extreme academic rigor, specific declarative knowledge, and fluid intelligence. This exam requires the user to possess prior domain knowledge. Superficial reading must be heavily penalized.

PSYCHOMETRIC MODEL & SCORE INTERPRETATION:
- Method: Rasch Model (IRT 1PL). Scores depend heavily on the calibrated difficulty of the item relative to the user's latent ability.
- Distractor Logic: Distractors must represent predictable procedural failures. 
- Components: Each of the 5 components is standardized to a Mean of 10 and Standard Deviation of 1.
- Total Score: Standardized to a Mean of 500 and Standard Deviation of 100. Highly competitive programs require scores >700."""

UNAL_DOMAINS = {
    "analisis_textual": """### DOMAIN: TEXTUAL ANALYSIS
- Overview: Deep, complex hermeneutic comprehension of high-level referential texts (Science, Humanities) and poetic-literary texts.
- Focus: High-level inferential and critical-intertextual reading.
- Topics: Deducing hidden premises, distinguishing strict semantic definitions, analyzing formal propositional logic applied to natural language, and deconstructing advanced rhetorical structures.
- Strategy: Use dense, academic paragraphs. Force the user to logically deconstruct the argument, identify logical fallacies, or deduce semantic implications that are deeply buried in the text's syntax.""",

    "matematicas": """### DOMAIN: MATHEMATICS
- Overview: Advanced mathematical modeling requiring rote procedural knowledge and pure abstract logic. 
- Focus: Numerical, Spatial, Metric, Random, and Variational thinking.
- Topics: Complex numbers, sequences, advanced algebra, polynomial factorization, limits, derivatives, analytic geometry (conics), and trigonometry (identities, equations).
- Strategy: Present rigorous mathematical problems. Do not provide the formulas. The user must deploy prior knowledge of theorems and equations to arrive at the solution. Distractors must be the result of common calculation or sign errors.""",

    "ciencias_naturales": """### DOMAIN: NATURAL SCIENCES
- Overview: Hard science evaluation requiring specific declarative knowledge of microscopic and macroscopic phenomenology.
- Components: 
  - Physics: Kinematics, dynamics, thermodynamics, fluid mechanics, electromagnetism, optics.
  - Chemistry: Stoichiometry, gas laws, electrochemistry, organic chemistry nomenclature, atomic models.
  - Biology: Mendelian and population genetics, cellular respiration and metabolism, biomolecules, ecology.
- Strategy: Present complex scientific problems requiring formula application and deep theoretical understanding. Require the user to synthesize laws.""",

    "ciencias_sociales": """### DOMAIN: SOCIAL SCIENCES
- Overview: Structural, chronological, and theoretical analysis of history, geography, and philosophy.
- Components: 
  - History & Geography: Global and Colombian history (e.g., 1886 to 1991 constitutional shifts), astronomical dynamics, physical geography (orography).
  - Philosophy & Logic: Classical to Contemporary thought. Formal propositional logic and syllogisms.
- Strategy: Ask specific questions requiring prior knowledge of historical ruptures or philosophical paradigms. Do not provide the answer implicitly in the text. Distractors should be accurate statements belonging to the wrong historical period or philosopher.""",

    "analisis_imagen": """### DOMAIN: IMAGE ANALYSIS
- Overview: Pure abstract logical reasoning, visuospatial cognition, and fluid intelligence. This is a unique hallmark of the UNAL exam.
- Focus: Mental rotation, deductive transformation, and comparative visual analytics.
- Topics: 
  - Isometry: Identifying orthogonal views (top, front, profile) of 3D solids.
  - Unfolding: Mentally assembling 3D shapes (Soma cubes, dice) from flat 2D templates.
  - Origami: Predicting the final shape of folded and cut paper.
  - Abstract Logic: Finding the missing piece in complex visual matrices (Tangram logic).
- Strategy: Since this is text-based AI, you must explicitly and rigorously describe the visual puzzle (e.g., "Imagine a 3D solid composed of 7 smaller cubes..."). Challenge the user to mentally rotate the object, identify the correct 2D projection, or deduce the next logical transformation in the series."""
}

GENERAL_FRAMEWORK = """## ACADEMIC FRAMEWORK: General University Preparation
GLOBAL STRATEGY: Build strong foundational knowledge across core academic subjects.

CRITICAL MISSION (EXAM DISCOVERY): 
The user has not yet specified which admission exam they are preparing for (ICFES Saber 11 or Universidad Nacional UNAL).
Strategy: Answer their immediate question clearly, but naturally ask them which specific exam or university they are targeting so you can tailor your future explanations, and offer to generate a simulacro."""

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