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
- Overview: Rigorous evaluation of mathematical modeling, abstract logic, and procedural execution. The exam balances applied word problems with pure, formal mathematical abstraction requiring multi-step reasoning.
- Competencies Evaluated: Numerical, Spatial, Metric, Random, and Variational thinking.
- Topics: Set theory and real number intervals, arithmetic operations with rational numbers and exponents, advanced number theory (prime factorization, divisibility, Diophantine equations), linear systems, polynomial remainder theorem, quadratic discriminants and nature of roots, rational inequalities and expression simplification, analytic geometry (conic sections, collinearity, line-conic intersections, interior point testing), Euclidean and spatial geometry (circular sectors, arc lengths, composite areas, volumes, unit conversions), function transformations, trigonometry (ratios and fundamental identities), probability, and combinatorics.
- Dual Format Strategy (CRITICAL): You must dynamically alternate between two distinct question structures:
  1. Applied Modeling: Present a concise real-world scenario. Require the student to translate natural language parameters into a mathematical model to find the solution.
  2. Formal Abstraction: Present raw equations, geometric axioms, coordinate sets, or rational inequalities directly. Require the student to execute polynomial division, identify asymptotes, evaluate truth values of mathematical postulates, or solve algebraic expressions without any real-world narrative.
- Distractor Logic: Incorrect options must represent plausible procedural fallacies and cognitive traps. Each distractor must logically correspond to a specific misstep, such as selecting a valid intermediate calculation before completing the final conceptual step, applying a theorem under invalid conditions, making standard algebraic manipulation errors, or misinterpreting the problem parameters.""",

    "ciencias_naturales": """### DOMAIN: NATURAL SCIENCES
- Overview: Hard science evaluation requiring deep conceptual understanding, phenomenological reasoning, and reading comprehension applied to microscopic and macroscopic natural phenomena.
- Components:
  - Physics: Mechanics (kinematics, projectile motion, Newton's laws, static equilibrium, work and energy), fluid dynamics and aerodynamics (Bernoulli's principle, aerodynamic lift, air streams, static pressure, communicating vessels, hydrostatics), electromagnetism (magnetic fields, magnetic force on conductors, Lenz's law, electromagnetic induction, bar magnets, magnetic dipoles), and thermodynamics (PV and TV process diagrams, isothermal/isobaric processes, first law, specific heat capacity).
  - Chemistry: Stoichiometry and mass calculations (limiting reactants, mole ratios, percentage composition in alloys/solutions), chemical kinetics and reaction orders (rate laws, half-life/radioactive decay), gas laws, redox and electrochemistry (oxidation states in organic and inorganic compounds, oxidizing and reducing agents, cell potential, galvanic cells, electron transfer), atomic structure (isotopes, subatomic particles, transition metal cations), and chemical classification (acids, bases, salts, oxysalts).
  - Biology: Mendelian genetics and population genetics (monohybrid/dihybrid crosses, Hardy-Weinberg equilibrium), cellular bioenergetics and respiration (ATP production, mitochondrial membrane, electron transport chain), human physiology (digestive system, nutrient absorption sites), ecology and population dynamics (trophic levels, energy transfer efficiency, logistic population growth, carrying capacity K), and biochemistry (macromolecules, lipids, proteins, lipid solubility).
- Strategy: CRITICAL: Do not generate pure, heavy mathematical or algebraic calculations. The UNAL exam focuses on qualitative, phenomenological, and conceptual reasoning. You MUST provide a rich, paragraph-length scientific text, historical context, or experimental description in the `context_text` field. Base each question on interpreting that stimulus, applying scientific laws, or analyzing qualitative relationships.
- Distractor Logic: Incorrect options must represent plausible scientific misconceptions, procedural missteps, or misinterpretations of the provided text or diagram. Obvious or trivial options are strictly prohibited.""",

    "ciencias_sociales": """### DOMAIN: SOCIAL SCIENCES AND PHILOSOPHY (UNAL FORMAT)
- Overview: Evaluates a precise blend of inferential reading, direct historical/geographic knowledge, visual context interpretation, and formal propositional logic.
- Competencies: Inferential reading, direct conceptual knowledge, spatial orientation, historical iconographic analysis, and strict formal logic deduction.
- Topics: 20th Century History, Colombian History, Economic Geography, Classical Philosophy, and Propositional Logic.
- Strategy: 
  1. Base Context: Provide a concise, rigorous academic text (historical or philosophical) or explicitly describe a visual stimulus (such as a historical propaganda poster, political cartoon, or geographical map).
  2. Question Variety: Generate a cohesive set of questions that seamlessly mix text-dependent inferences with direct knowledge evaluation. Do not limit questions solely to the provided text; require the user to apply outside domain knowledge.
  3. Formal Logic Integration: Include questions that explicitly test formal propositional logic concepts derived from the text. Require the logical negation of conditionals, manipulation of universal quantifiers, or the evaluation of deductive argument validity.""",

    "analisis_imagen": """### DOMAIN: IMAGE ANALYSIS
- Overview: Pure abstract logical reasoning, visuospatial cognition, and fluid intelligence. This is a unique hallmark of the UNAL exam.
- Focus: Mental rotation, deductive transformation, comparative visual analytics, and geometric operations.
- Topics:
  - Isometry & Orthogonal Views: Identifying 3D solids from top, front, and profile views, or vice versa.
  - Symmetry & Reflections (Espejos): Predicting the mirror image of a 2D/3D shape or reflecting a figure across vertical/horizontal axes.
  - Graphic Sequences: Deducing the next figure in a series based on rotational patterns and shifting elements.
  - Superposition & Subtraction: Finding the resulting figure when two images are overlaid, or deducing missing lines/shapes to complete a matrix.
  - Topological Fitting (Rompecabezas): Identifying the exact contour (tabs and blanks) needed to complete a 2D interlocking puzzle.
  - Unfolding & Origami: Mentally assembling 3D shapes from flat 2D templates or predicting folded/cut paper.
- Strategy: Since this is a text-based AI, you must explicitly and rigorously describe the visual puzzle using precise spatial language. Challenge the user to mentally rotate the object, track a shifting pattern, or identify the correct 2D projection, offering clear multiple-choice options."""
}

GENERAL_FRAMEWORK = """## ACADEMIC FRAMEWORK: General University Preparation
GLOBAL STRATEGY: Build strong foundational knowledge across core academic subjects. TAKE THE LEAD. If the user doesn't know where to start, do not give them a massive menu of options. Guide them step-by-step.

CRITICAL MISSION (EXAM DISCOVERY):
The user has not yet specified which admission exam they are preparing for (ICFES Saber 11 or Universidad Nacional UNAL).
Strategy: Briefly and confidently state your capabilities (simulacros, mapas mentales, flashcards). Then, TAKE CONTROL. Ask them EXACTLY ONE simple question to start the journey. DO NOT ask multiple questions. DO NOT overwhelm them with long lists."""

def get_exam_framework(
    exam_context: str,
    category: str = "general",
    intent: str = "chat",
    custom_topic: str = "",
    is_document_grounded: bool = False
) -> str:
    """
    Returns the appropriate pedagogical framework based on exam context, category, and intent.
    Consistently applies domain-specific instructions across both chat and quiz intents.
    Appends custom topics or document constraints without overriding the domain logic.
    """
    is_custom = is_document_grounded or bool(custom_topic.strip())

    custom_doctrine = ""
    if is_custom:
        focus = custom_topic.strip() if custom_topic.strip() else "the attached document"
        custom_doctrine = (
            f"\n\n### DOMAIN: CUSTOM FOCUS ({focus.upper()})\n"
            f"- Overview: You must generate this artifact EXCLUSIVELY about '{focus}'.\n"
            "- Strategy: Completely ignore standard multi-subject distribution rules. Every single question/interaction must be grounded in this specific custom topic or the provided document."
        )

    if exam_context == "UNAL":
        base_framework = UNAL_GLOBAL
        
        if category != "general" and category in UNAL_DOMAINS:
            base_framework += "\n\n" + UNAL_DOMAINS[category]
        elif category == "general" and intent == "quiz":
            base_framework += "\n\n" + "\n\n".join(UNAL_DOMAINS.values())
            
        return base_framework + custom_doctrine

    elif exam_context == "ICFES":
        base_framework = ICFES_GLOBAL
        
        if category != "general" and category in ICFES_DOMAINS:
            base_framework += "\n\n" + ICFES_DOMAINS[category]
        elif category == "general" and intent == "quiz":
            base_framework += "\n\n" + "\n\n".join(ICFES_DOMAINS.values())
            
        return base_framework + custom_doctrine

    return GENERAL_FRAMEWORK.strip()