# src/schemas/mindmap_schemas.py
from typing import List
from pydantic import BaseModel, Field

class MindMapNode(BaseModel):
    id: int = Field(
        description="A unique integer ID for the node. The root node should typically be ID 1."
    )
    label: str = Field(
        description="The short text to display. Keep it concise."
    )
    level: int = Field(
        description="The hierarchy level. 0 for the central root topic, 1 for main categories, 2 for sub-categories, 3 for specific details."
    )

class MindMapEdge(BaseModel):
    source: int = Field(
        alias="from", 
        description="The ID of the parent node."
    )
    to: int = Field(
        description="The ID of the child node."
    )

class MindMapPayload(BaseModel):
    thought_process: str = Field(
        description="REQUIRED: Draft your tree structure here FIRST. Outline the root, main categories, and sub-categories to ensure a balanced, multi-level hierarchy before populating the nodes and edges."
    )
    title: str = Field(
        description="The formal academic name of the core subject matter."
    )
    nodes: List[MindMapNode] = Field(
        description="The list of concept boxes."
    )
    edges: List[MindMapEdge] = Field(
        description="The list of connections indicating the parent-child relationships between boxes."
    )