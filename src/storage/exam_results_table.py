# src/storage/exam_results_table.py
import boto3
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserExamResults")

def save_exam_result(
    user_id: str,
    exam_id: str,
    total_score: float,
    time_used_seconds: int,
    subject_scores: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Saves a user's exam result to the UserExamResults DynamoDB table.
    """
    if not user_id or not exam_id:
        raise ValueError("user_id and exam_id are required to save an exam result.")

    timestamp = datetime.utcnow().isoformat()
    
    item = {
        "UserId": user_id,
        "Timestamp": timestamp,
        "ExamId": exam_id,
        "TotalScore": total_score,
        "TimeUsedSeconds": time_used_seconds
    }

    if subject_scores:
        item["SubjectScores"] = subject_scores

    try:
        table.put_item(Item=item)
        logger.info(f"Successfully saved exam result for UserId: {user_id}, ExamId: {exam_id}")
    except Exception as e:
        logger.error(f"Failed to save exam result for UserId {user_id}: {e}")
        raise e

    return item

def get_exam_leaderboard(exam_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetches the top scores for a specific exam using the ExamLeaderboardIndex.
    """
    if not exam_id:
        raise ValueError("exam_id is required to fetch a leaderboard.")

    try:
        response = table.query(
            IndexName='ExamLeaderboardIndex',
            KeyConditionExpression=Key('ExamId').eq(exam_id),
            ScanIndexForward=False, 
            Limit=limit
        )
        return response.get("Items", [])
    except Exception as e:
        logger.error(f"Failed to fetch leaderboard for ExamId {exam_id}: {e}")
        return []

def get_user_exam_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetches the chronological exam history for a specific user.
    """
    if not user_id:
        raise ValueError("user_id is required to fetch exam history.")

    try:
        response = table.query(
            KeyConditionExpression=Key('UserId').eq(user_id),
            ScanIndexForward=False,
            Limit=limit
        )
        return response.get("Items", [])
    except Exception as e:
        logger.error(f"Failed to fetch exam history for UserId {user_id}: {e}")
        return []