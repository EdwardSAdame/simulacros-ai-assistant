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
        usage_id: str,           # 🟢 NEW: Unique ID for the record (Partition Key)
        user_id: str, 
        timestamp: str, 
        conversation_id: str,    # 🟢 FIX: Renamed to strictly use conversation_id
        total_tokens: int,       # 🟢 FIX: Main billing metric kept at the top level
        metadata: dict           # 🟢 NEW: Encapsulates tier, engine, input/output tokens, etc.
    ) -> bool:
        """
        Saves a single token usage record to DynamoDB using PascalCase 
        and a strictly normalized FinOps schema.
        """
        try:
            item = {
                'UsageId': usage_id,
                'UserId': user_id,
                'Timestamp': timestamp,
                'ConversationId': conversation_id,
                'TotalTokens': total_tokens,
                'Metadata': metadata
            }
            
            self.table.put_item(Item=item)
            log_event(
                event_type="token_usage_recorded", 
                details={
                    "UsageId": usage_id, 
                    "ConversationId": conversation_id, 
                    "TotalTokens": total_tokens
                }
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
        Retrieves all token usage records for a specific user using the UserIndex.
        """
        try:
            response = self.table.query(
                IndexName='UserIndex', # 🟢 NEW: Added index since UsageId is now the PK
                KeyConditionExpression=boto3.dynamodb.conditions.Key('UserId').eq(user_id)
            )
            return response.get('Items', [])
            
        except ClientError as e:
            log_event(
                event_type="token_usage_retrieve_failed", 
                details={"UserId": user_id, "error": e.response['Error']['Message']}, 
                level="error", 
                error=e
            )
            return []

    def get_conversation_usage(self, conversation_id: str) -> list: # 🟢 FIX: Renamed function
        """
        Retrieves all token usage records for a specific conversation using the ConversationIndex.
        """
        try:
            response = self.table.query(
                IndexName='ConversationIndex', # 🟢 FIX: Updated index name
                KeyConditionExpression=boto3.dynamodb.conditions.Key('ConversationId').eq(conversation_id)
            )
            return response.get('Items', [])
            
        except ClientError as e:
            log_event(
                event_type="token_usage_conversation_retrieve_failed", 
                details={"ConversationId": conversation_id, "error": e.response['Error']['Message']}, 
                level="error", 
                error=e
            )
            return []