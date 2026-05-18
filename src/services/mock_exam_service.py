import os
import json
import logging
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)

class MockExamService:
    """
    Dedicated service to fetch and serve static historical exams (Mock Exams / Simulacros).
    Supports fetching the catalog menu for the UI, and fetching specific exam volumes.
    """

    @classmethod
    def get_catalog(cls, exam_type: str) -> Tuple[str, Optional[Dict]]:
        """
        Fetches the lightweight catalog JSON used to populate frontend repeaters.
        
        Args:
            exam_type (str): The main exam category (e.g., "icfes", "unal").
            
        Returns:
            Tuple[str, dict]: A success message and the parsed catalog JSON data.
        """
        try:
            clean_exam_type = exam_type.lower()
            
            # Construct absolute path to the catalog file
            # e.g., src/knowledge/icfes/general/icfes_exam.json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            target_file = os.path.join(base_dir, "knowledge", clean_exam_type, "general", f"{clean_exam_type}_exam.json")
            
            if not os.path.exists(target_file):
                logger.error(f"Catalog file not found: {target_file}")
                return "Error: No se encontró el catálogo de simulacros.", None

            logger.info(f"Serving exam catalog for: {clean_exam_type}")

            with open(target_file, 'r', encoding='utf-8') as f:
                catalog_data = json.load(f)

            return "Catálogo cargado con éxito.", catalog_data

        except Exception as e:
            logger.error(f"Failed to load catalog for {exam_type}: {e}", exc_info=True)
            return "**Error**: Hubo un problema al cargar el catálogo de simulacros.", None


    @classmethod
    def get_specific_exam(cls, exam_type: str, component: str, exam_id: str) -> Tuple[str, Optional[Dict]]:
        """
        Fetches a specific static exam JSON payload based on its filename.
        
        Args:
            exam_type (str): The main exam category (e.g., "icfes").
            component (str): The specific subject module (e.g., "matematicas").
            exam_id (str): The exact filename of the exam (e.g., "math_vol_02.json").
            
        Returns:
            Tuple[str, dict]: A success message and the parsed JSON data.
        """
        try:
            # 1. Map component names to folder names
            clean_component = component.replace("-", "_").lower()
            clean_exam_type = exam_type.lower()
            
            # Security: Ensure exam_id is just a filename to prevent directory traversal
            secure_exam_id = os.path.basename(exam_id)
            
            # 2. Construct absolute path to the specific file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, "knowledge", clean_exam_type, clean_component, secure_exam_id)
            
            if not os.path.exists(file_path):
                logger.error(f"Exam file not found: {file_path}")
                return "Error: El simulacro solicitado no existe o fue removido.", None

            logger.info(f"Serving specific static exam: {clean_exam_type}/{clean_component} -> {secure_exam_id}")

            # 3. Read and return the JSON content
            with open(file_path, 'r', encoding='utf-8') as f:
                exam_data = json.load(f)

            # 4. Structure it exactly as your frontend widget expects
            meta_payload = {
                "type": "static_exam_data",
                "exam_data": exam_data
            }
            
            success_message = "¡Simulacro cargado con éxito! Buena suerte."
            return success_message, meta_payload

        except Exception as e:
            logger.error(f"Failed to load specific exam {exam_id} for {exam_type}/{component}: {e}", exc_info=True)
            return "**Error**: Hubo un problema al cargar el simulacro histórico.", None