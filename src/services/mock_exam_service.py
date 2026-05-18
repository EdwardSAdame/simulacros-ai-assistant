import os
import json
import random
import logging
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)

class MockExamService:
    """
    Dedicated service to fetch and serve static historical exams (Mock Exams / Simulacros).
    It randomly selects an available JSON volume for a given exam type and component.
    """

    @classmethod
    def get_random_exam(cls, exam_type: str, component: str) -> Tuple[str, Optional[Dict]]:
        """
        Fetches a random static exam JSON payload.
        
        Args:
            exam_type (str): The main exam category (e.g., "icfes", "unal").
            component (str): The specific subject module (e.g., "matematicas", "ingles").
            
        Returns:
            Tuple[str, dict]: A success message and the parsed JSON data.
        """
        try:
            # 1. Map component names to folder names if necessary to ensure exact match
            # e.g., "ciencias-naturales" from Wix should map to "ciencias_naturales" folder
            clean_component = component.replace("-", "_").lower()
            clean_exam_type = exam_type.lower()
            
            # 2. Construct absolute path to the knowledge directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            target_dir = os.path.join(base_dir, "knowledge", clean_exam_type, clean_component)
            
            if not os.path.exists(target_dir):
                logger.error(f"Directory not found: {target_dir}")
                return "Error: No se encontró la base de datos para este componente.", None

            # 3. Find all JSON files in the folder
            json_files = [f for f in os.listdir(target_dir) if f.endswith('.json')]
            
            if not json_files:
                logger.error(f"No JSON files found in directory: {target_dir}")
                return "Error: No hay simulacros disponibles para esta materia en este momento.", None

            # 4. Pick a random volume
            selected_file = random.choice(json_files)
            file_path = os.path.join(target_dir, selected_file)
            
            logger.info(f"Serving static exam: {exam_type}/{clean_component} -> {selected_file}")

            # 5. Read and return the JSON content
            with open(file_path, 'r', encoding='utf-8') as f:
                exam_data = json.load(f)

            # We structure it exactly as your frontend widget expects
            meta_payload = {
                "type": "static_exam_data",
                "exam_data": exam_data
            }
            
            success_message = "¡Simulacro cargado con éxito! Buena suerte."
            return success_message, meta_payload

        except Exception as e:
            logger.error(f"Failed to load static exam for {exam_type}/{component}: {e}")
            return "**Error**: Hubo un problema al cargar el simulacro histórico.", None