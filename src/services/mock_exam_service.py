import os
import json
import random
import logging
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)

class MockExamService:
    """
    Dedicated service to generate dynamic catalog menus for Mock Exams.
    """

    @classmethod
    def get_catalog(cls, exam_type: str) -> Tuple[str, Optional[Dict]]:
        """
        Fetches the catalog JSON, groups by component, and selects one random volume per component.
        
        Args:
            exam_type (str): The main exam category (e.g., "icfes").
            
        Returns:
            Tuple[str, dict]: A success message and the parsed catalog JSON data containing exactly one exam per component.
        """
        try:
            clean_exam_type = exam_type.lower()
            
            # Construct absolute path to the catalog file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            target_file = os.path.join(base_dir, "knowledge", clean_exam_type, "general", f"{clean_exam_type}_exam.json")
            
            if not os.path.exists(target_file):
                logger.error(f"Catalog file not found: {target_file}")
                return "Error: No se encontró el catálogo de simulacros.", None

            logger.info(f"Generating dynamic exam catalog for: {clean_exam_type}")

            with open(target_file, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)

            # Extract the raw list of all exams
            all_exams = catalog_data.get("catalog", [])
            
            # Group exams by componentId
            grouped_exams = {}
            for exam in all_exams:
                comp_id = exam.get("componentId")
                if comp_id not in grouped_exams:
                    grouped_exams[comp_id] = []
                grouped_exams[comp_id].append(exam)
                
            # Select one random exam per component
            dynamic_catalog = []
            for comp_id, exams_list in grouped_exams.items():
                selected_exam = random.choice(exams_list)
                dynamic_catalog.append(selected_exam)

            # Return the filtered list to the frontend
            return "Catálogo cargado con éxito.", {"catalog": dynamic_catalog}

        except Exception as e:
            logger.error(f"Failed to load catalog for {exam_type}: {e}", exc_info=True)
            return "**Error**: Hubo un problema al cargar el catálogo de simulacros.", None