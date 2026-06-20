# src/services/exam_results_service.py
import logging
from typing import Dict, Any, List, Optional
from src.storage.exam_results_table import save_exam_result, get_exam_leaderboard, get_user_exam_history

logger = logging.getLogger(__name__)

def process_and_save_exam(
    user_id: str,
    exam_id: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validates and processes exam results from the frontend before saving to the database.
    """
    if not user_id or not exam_id:
        raise ValueError("user_id and exam_id must be provided to process the exam.")

    # Extract and cast data from the frontend payload safely
    try:
        total_score = float(payload.get("finalScore", 0.0))
        time_used_seconds = int(payload.get("timeUsedSeconds", 0))
        subject_scores = payload.get("subjectScores", None)
    except ValueError as e:
        logger.error(f"Invalid data types in exam payload: {e}")
        raise ValueError("finalScore and timeUsedSeconds must be numeric values.")

    # Basic business logic validation
    if total_score < 0:
        total_score = 0.0
    if time_used_seconds < 0:
        time_used_seconds = 0

    try:
        saved_record = save_exam_result(
            user_id=user_id,
            exam_id=exam_id,
            total_score=total_score,
            time_used_seconds=time_used_seconds,
            subject_scores=subject_scores
        )
        logger.info(f"Successfully processed and saved exam {exam_id} for user {user_id}")
        return saved_record
    except Exception as e:
        logger.error(f"Service layer error saving exam result: {e}")
        raise e

def get_leaderboard_data(exam_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves the leaderboard data for a specific exam.
    """
    if not exam_id:
        raise ValueError("exam_id is required to fetch leaderboard data.")
        
    try:
        return get_exam_leaderboard(exam_id=exam_id, limit=limit)
    except Exception as e:
        logger.error(f"Service layer error fetching leaderboard: {e}")
        return []

def get_user_progress(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves the exam history for a user to display their progress over time.
    """
    if not user_id:
        raise ValueError("user_id is required to fetch user progress.")
        
    try:
        return get_user_exam_history(user_id=user_id, limit=limit)
    except Exception as e:
        logger.error(f"Service layer error fetching user progress: {e}")
        return []