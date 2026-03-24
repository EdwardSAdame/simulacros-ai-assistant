import os
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

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
            logger.info(f"Successfully recorded token usage for user {user_id} and model {model}.")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to record token usage: {e.response['Error']['Message']}")
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
            logger.error(f"Failed to retrieve token usage for user {user_id}: {e.response['Error']['Message']}")
            return []