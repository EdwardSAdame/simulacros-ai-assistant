# src/schemas/mindmap_schemas.py
from typing import List
from pydantic import BaseModel, Field

class MindMapNode(BaseModel):
    id: int = Field(
        description="A unique integer ID for the node. The root node should typically be ID 1."
    )
    label: str = Field(
        description="The short text to display inside the box. Keep it concise (1-4 words max)."
    )
    level: int = Field(
        description="The hierarchy level. 0 for the central root topic, 1 for main branches, 2 for sub-branches, etc."
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
    title: str = Field(
        description="A concise and highly accurate academic title for this specific mind map."
    )
    nodes: List[MindMapNode] = Field(
        description="The list of concept boxes."
    )
    edges: List[MindMapEdge] = Field(
        description="The list of connections indicating the parent-child relationships between boxes."
    )