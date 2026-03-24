# src/storage/token_usage_table.py
import os
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from src.utils.logging_utils import log_event

class TokenUsageTable:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('TOKEN_USAGE_TABLE_NAME', 'TokenUsage')
        self.table = self.dynamodb.Table(self.table_name)

    def record_usage(
        self, 
        user_id: str, 
        timestamp: str, 
        session_id: str, 
        model: str, 
        prompt_tokens: int, 
        completion_tokens: int, 
        total_tokens: int,
        reasoning_tokens: Optional[int] = 0,
        cached_tokens: Optional[int] = 0
    ) -> bool:
        """
        Saves a single token usage record to DynamoDB.
        """
        try:
            item = {
                'userId': user_id,
                'timestamp': timestamp,
                'sessionId': session_id,
                'model': model,
                'promptTokens': prompt_tokens,
                'completionTokens': completion_tokens,
                'totalTokens': total_tokens,
                'reasoningTokens': reasoning_tokens,
                'cachedTokens': cached_tokens
            }
            
            self.table.put_item(Item=item)
            log_event(
                event_type="token_usage_recorded", 
                details={"user_id": user_id, "model": model, "total_tokens": total_tokens}
            )
            return True
            
        except ClientError as e:
            log_event(
                event_type="token_usage_record_failed", 
                details={"error": e.response['Error']['Message']}, 
                level="error", 
                error=e
            )
            return False

    def get_user_usage(self, user_id: str) -> list:
        """
        Retrieves all token usage records for a specific user.
        """
        try:
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id)
            )
            return response.get('Items', [])
            
        except ClientError as e:
            log_event(
                event_type="token_usage_retrieve_failed", 
                details={"user_id": user_id, "error": e.response['Error']['Message']}, 
                level="error", 
                error=e
            )
            return []