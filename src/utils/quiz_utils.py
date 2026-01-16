# src/utils/quiz_utils.py
import random
import logging
from src.schemas.quiz_schemas import QuizQuestion

logger = logging.getLogger(__name__)

class QuizUtils:
    """
    Utilities for processing and validating quiz data structures.
    """

    @staticmethod
    def shuffle_options(question: QuizQuestion):
        """
        Shuffles the options of a question in-place and updates the correct_option_index.
        This neutralizes the LLM bias of always putting the correct answer first.
        """
        try:
            # 1. Identify the correct option object before shuffling
            if 0 <= question.correct_option_index < len(question.options):
                correct_option_obj = question.options[question.correct_option_index]
            else:
                # Fallback if index is out of bounds (shouldn't happen with strict schema)
                return

            # 2. Shuffle the options list
            random.shuffle(question.options)

            # 3. Find the new index of the correct option
            # We use 'is' for object identity or compare fields if necessary
            new_index = -1
            for i, opt in enumerate(question.options):
                if opt == correct_option_obj:
                    new_index = i
                    break
            
            # 4. Update the index
            if new_index != -1:
                question.correct_option_index = new_index
                
        except Exception as e:
            logger.error(f"Error shuffling options: {e}")