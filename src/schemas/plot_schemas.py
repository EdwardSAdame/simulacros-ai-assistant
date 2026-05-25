from pydantic import BaseModel, Field

class PlotGenerationBlueprint(BaseModel):
    analytical_concept: str = Field(
        description="The core mathematical, scientific, or data concept to be visualized."
    )
    chart_type: str = Field(
        description="The appropriate chart type for the analytical data."
    )
    data_generation_rules: str = Field(
        description="Strict instructions on what data the code must generate. Example: 'Generate x linearly spaced from 0 to 2*pi, calculate y = sin(x)'."
    )
    axis_labels: str = Field(
        description="The analytical labels for the X and Y axes representing the variables being plotted."
    )