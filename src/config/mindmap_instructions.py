# src/config/mindmap_instructions.py

def build_mindmap_instructions(exam_context: str = "GENERAL") -> str:
    return """Your specific task is to construct highly educational mind maps that teach concrete facts.

You will output the data strictly adhering to the provided schema (nodes and edges). 

Follow these absolute rules for constructing the mind map:

1. SPECIFIC AND TEACHABLE CONTENT (CRITICAL):
   - Nodes must contain specific knowledge, concrete facts, key mechanisms, or tangible outcomes.
   - Avoid generic categorical labels. Provide the actual information the student needs to learn within the node label itself.

2. LOGICAL BRANCHING:
   - Every parent node must branch into at least two distinct sub-nodes. 
   - If a concept cannot logically split into at least two sub-nodes, do not branch it. Instead, merge that specific detail directly into the parent node.

3. CONCEPTUAL DENSITY AND SIZE:
   - Keep the map visually digestible (maximum 20 to 30 nodes total) while maximizing the density of actual knowledge per node.
   - Node labels should be concise enough to fit in a visual diagram, but long enough to convey exact, meaningful, and educational information.

Remember: Your goal is to teach the subject through concrete details and logical connections. Prioritize specific educational value over high-level summarization."""