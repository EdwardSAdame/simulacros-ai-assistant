# src/config/exam_frameworks.py

ICFES_FRAMEWORK = """
## ACADEMIC FRAMEWORK: ICFES Saber 11
GLOBAL STRATEGY: Focus on competency-based evaluation and psychometric awareness. The exam uses Item Response Theory (IRT), evaluating difficulty, discrimination, and pseudo-guessing. The AI must train the user to avoid erratic guessing patterns. Note the asymmetric scoring model (Math, Reading, Sciences, Social = 3x weight; English = 1x weight).
DISTRACTOR LOGIC: The AI must craft and explain distractors that are factually true statements in the real world (e.g., a valid legal principle or a true biological fact) but are contextually irrelevant to the specific prompt. Always enforce the "most specific response" rule.

### DOMAIN: MATHEMATICS (QUANTITATIVE REASONING)
- Overview: Evaluates generic (daily life citizen math) and non-generic (STEM-focused) competencies. Highly focused on data literacy and real-world application.
- Focus: Interpretation of abstract data, strategic problem-solving planning, and logical justification.
- Topics: Statistics & Probability (charts, variance, combinations/permutations, percentiles), Geometry (spatial modeling, transformations, Pythagorean applications), Algebra & Calculus (linear/quadratic/exponential functions, rates of change).
- Strategy: Present scenarios involving tables, charts, or economic data. Provide rigorous derivations using LaTeX: \\( \\) for inline and \\[ \\] for blocks.

### DOMAIN: CRITICAL READING
- Overview: Hermeneutic comprehension evaluating both continuous texts (essays, novels, philosophy) and discontinuous texts (infographics, comics, data tables).
- Focus: Literal, Inferential, and Critical-Intertextual levels.
- Topics: Extracting local semantic elements, uncovering text macrostructures, deducing implicit premises, identifying formal/informal fallacies, and unmasking ideological biases.
- Strategy: Describe visual texts (infographics/comics) clearly if simulating discontinuous texts. Force the user to differentiate between the author's main thesis and secondary supporting data.

### DOMAIN: SOCIAL AND CITIZEN SCIENCES
- Overview: Integration of history, geography, economics, and constitutional citizenship. Evaluates the ability to map social problems systemically.
- Focus: Social thinking, perspective analysis, and systemic/reflective thinking.
- Topics: Colombian Constitution of 1991 (mechanisms of citizen participation, branches of power, state of rights), 20th/21st-century Colombian history (violence, peace agreements, socioeconomic shifts), and global economic impacts.
- Strategy: When analyzing perspectives, force the user to suspend their own moral/ethical judgment. The correct answer must strictly reflect the logical internal interest of the actor described in the prompt, regardless of ethical alignment.

### DOMAIN: NATURAL SCIENCES
- Overview: Applied phenomenological problem-solving combining Biology, Chemistry, Physics, and CTS (Science, Technology, and Society).
- Focus: Iconographic analysis and experimental design. The core data to solve the problem should often be embedded in described graphs, circuits, or diagrams rather than just the introductory text.
- Topics: Biology (cellular transport, central dogma/protein synthesis, mitosis vs meiosis, Mendelian genetics, ecology), Chemistry (periodic trends, bonding, stoichiometry, conservation of mass), Physics (kinematics, Newton's laws, thermodynamics, mechanical energy conservation).
- Strategy: Present experimental setups. Ask the user to validate hypotheses, identify controlled/dependent variables, or extrapolate conclusions from empirical data sets.

### DOMAIN: ENGLISH
- Overview: Evaluates communicative, pragmatic, lexical, and grammatical competence aligned with the CEFR (levels A- to B1+).
- Focus: 7 distinct parts of progressive difficulty measuring specific cognitive-linguistic skills.
- Topics: Part 1 (Lexical matching), Part 2 (Pragmatic signs and physical locations), Part 3 (Conversational coherence), Part 4 (Basic grammar cloze), Part 5 (Literal reading comprehension), Part 6 (Inferential reading comprehension), Part 7 (Advanced lexico-grammatical cloze).
- Strategy: Clearly identify which of the 7 parts is being simulated. Provide culturally relevant contexts and test specific structural rules (e.g., modals, perfect tenses, conditionals).
"""

UNAL_FRAMEWORK = """
## ACADEMIC FRAMEWORK: Universidad Nacional de Colombia (UNAL) Admission Exam
GLOBAL STRATEGY: Focus on deep analytical rigor, advanced problem-solving, and psychometric awareness. Every interaction must demonstrate "Reconocimiento" (Recognition) and "Uso Significativo" (Meaningful Use) of academic codes.

### DOMAIN: TEXTUAL ANALYSIS
- Overview: Deep hermeneutic comprehension of referential texts (Science, Humanities) and poetic-literary texts.
- Focus: Penalize superficial reading. Heavily emphasize Inferential and Critical-Intertextual levels.
- Topics: Deducing hidden premises, differentiating strict semantic definitions, judging authorial ideological bias, distinguishing facts from opinions, and applying mathematical propositional logic to natural language statements.
- Strategy: Analyze syntax, semantics, and authorial intent. Deconstruct arguments logically to find underlying meanings.

### DOMAIN: MATHEMATICS
- Overview: Mathematical modeling and translating natural language into formal algebraic/geometric structures. Rote memorization of formulas is insufficient.
- Focus: Numerical, Spatial, Metric, Random, and Variational thinking.
- Topics: Number hierarchies, system of equations (geometric interpretation), quadratic discriminants, geometric optimization (areas/volumes), analytic geometry (conics, slopes), function transformations, parity (even/odd), trigonometric identities, combinatorics (permutations vs. combinations), and expected value.
- Strategy: Stimulate reflection through the interpretation of schemes. Provide rigorous derivations using LaTeX: \\( \\) for inline and \\[ \\] for blocks.

### DOMAIN: NATURAL SCIENCES
- Overview: Interdisciplinary phenomenology combining macroscopic principles, atomic reactivity, and cellular metabolism within single experimental scenarios.
- Components: 
    - Physics: Galilean relativity, free-body diagrams, mechanical energy conservation, fluid dynamics (Archimedes, Bernoulli).
    - Chemistry: Periodic trends, Lewis structures, strict stoichiometry.
    - Biology: Cellular organelles, central dogma, mitosis vs. meiosis, Mendelian genetics (Punnett squares), trophic network thermodynamics.
- Strategy: Prioritize the analysis of concepts and processes represented in schemas. Focus on synthesis, deduction, and the application of fundamental laws.

### DOMAIN: SOCIAL SCIENCES
- Overview: Structural analysis of historical causalities, geographical systems, and philosophical arguments.
- Components: 
    - History: Epistemic ruptures (Renaissance, Revolutions), Colombian constitutional evolution (1886 to 1991).
    - Geography: Astronomical dynamics, Colombian orography and thermal floors, global demographics.
    - Philosophy & Logic: Classical to Contemporary thought (Plato, Descartes, Kant, Marx, Nietzsche, Freud), formal propositional logic, syllogisms, and informal fallacies.
- Strategy: Analyze social phenomena through contextualized problems. Evaluate the ability to use social science codes to solve complex situational queries.

### DOMAIN: IMAGE ANALYSIS
- Overview: Pure abstract logical reasoning, fluid intelligence, and visuospatial cognition. This is the highest statistical differentiator in the exam.
- Focus: Mental rotation, deductive transformation, and comparative visual analytics.
- Topics: Orthogonal views and 3D isometry, unfolding flat templates with symbols into 3D solids, differentiating specular reflections (mirror effect) from planar rotations, dynamic origami (predicting unfolded cuts), and spatial logic sequences.
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