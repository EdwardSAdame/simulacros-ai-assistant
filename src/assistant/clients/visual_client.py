# src/assistant/clients/visual_client.py
import logging
from typing import List, Dict, Any, Tuple

from src.config.settings import get_openai_client, get_code_interpreter_memory
from src.config.model_config import get_model_config
from src.schemas.plot_schemas import PlotGenerationBlueprint
from src.config.visual_instructions import build_visual_instructions
from src.assistant.artifact_handler import handle_generated_files

from .base_client import BaseAssistantClient

logger = logging.getLogger(__name__)

class VisualClient:
    """
    Handles structured plot blueprint generation and code interpreter execution.
    """

    @staticmethod
    def generate_plot_blueprint(
        conversation_input: List[Dict[str, Any]],
        mode: str,
        system_instruction: str
    ) -> Tuple[PlotGenerationBlueprint, Dict[str, int]]:
        """
        Generates a strict JSON blueprint detailing the analytical structure 
        of the required plot, without executing code.
        """
        client = get_openai_client()
        cfg = get_model_config(mode)

        api_input = [{"role": "system", "content": [{"type": "input_text", "text": system_instruction}]}]
        api_input.extend(conversation_input)

        req = BaseAssistantClient.build_request_payload(cfg, api_input, tools=None)
        req["text_format"] = PlotGenerationBlueprint

        try:
            resp = client.responses.parse(**req)
            
            parsed_data = None
            if hasattr(resp, 'output_parsed') and resp.output_parsed:
                parsed_data = resp.output_parsed
            else:
                for out in getattr(resp, 'output', []):
                    if getattr(out, "type", "") == "message":
                        for item in getattr(out, "content", []):
                            if getattr(item, "parsed", None):
                                parsed_data = item.parsed
                                break

            if not parsed_data:
                raise ValueError("Failed to parse PlotGenerationBlueprint from Responses API.")

            usage_data = BaseAssistantClient.extract_usage_metrics(getattr(resp, "usage", None))
            return parsed_data, usage_data
        except Exception as e:
            logger.error(f"Failed to generate plot blueprint: {e}")
            raise e

    @staticmethod
    def execute_plot_generation(
        blueprint: PlotGenerationBlueprint,
        mode: str,
        active_container_id: str | None
    ) -> Tuple[List[str], str | None, Dict[str, int]]:
        """
        Executes the code interpreter using the analytical blueprint combined 
        with the strict visual doctrine rules.
        """
        client = get_openai_client()
        cfg = get_model_config(mode)
        visual_rules = build_visual_instructions()

        prompt = (
            f"You are the visual engine. You MUST use the python tool (Code Interpreter) "
            f"to write and execute code for the following analytical blueprint:\n\n"
            f"--- ANALYTICAL BLUEPRINT ---\n"
            f"Concept: {blueprint.analytical_concept}\n"
            f"Chart Type: {blueprint.chart_type}\n"
            f"Data Generation: {blueprint.data_generation_rules}\n"
            f"Axes Labels: {blueprint.axis_labels}\n\n"
            f"--- VISUAL DOCTRINE (STRICT) ---\n"
            f"{visual_rules}\n\n"
            f"CRITICAL: Do NOT provide conversational text or raw Python text. You MUST execute it."
        )

        api_input = [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}]

        memory_limit = get_code_interpreter_memory()
        container_config = active_container_id if active_container_id else {"type": "auto", "memory_limit": memory_limit}
        tools = [{"type": "code_interpreter", "container": container_config}]

        req = BaseAssistantClient.build_request_payload(cfg, api_input, tools=tools)
        req["tool_choice"] = "required"

        try:
            resp = client.responses.create(**req)

            output_list = getattr(resp, "output", []) or []
            container_id = BaseAssistantClient.extract_container_id(output_list)

            generated_urls_map = handle_generated_files(client, resp, folder="chat_assets")
            generated_urls = list(generated_urls_map.values()) if isinstance(generated_urls_map, dict) else generated_urls_map
            usage_data = BaseAssistantClient.extract_usage_metrics(getattr(resp, "usage", None))

            return generated_urls, container_id, usage_data
        except Exception as e:
            logger.error(f"Failed to execute plot generation: {e}")
            raise e