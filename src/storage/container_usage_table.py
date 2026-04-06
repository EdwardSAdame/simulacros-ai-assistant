# src/storage/container_usage_table.py
import os
import boto3
from botocore.exceptions import ClientError
from src.utils.logging_utils import log_event

class ContainerUsageTable:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('CONTAINER_USAGE_TABLE_NAME', 'ContainerUsage')
        self.table = self.dynamodb.Table(self.table_name)

    def record_container_usage(
        self, 
        user_id: str, 
        timestamp: str, 
        conversation_id: str,  
        container_id: str, 
        memory_limit: str,
        metadata: dict = None # 🟢 NEW: Added metadata parameter
    ) -> bool:
        """
        Saves a single container usage record to DynamoDB.
        Uses PascalCase for database keys to match conventions.
        """
        try:
            item = {
                'UserId': user_id,
                'Timestamp': timestamp,
                'ConversationId': conversation_id, 
                'ContainerId': container_id,
                'MemoryLimit': memory_limit
            }
            
            # 🟢 NEW: Safely append Metadata if it was provided
            if metadata:
                item['Metadata'] = metadata
            
            self.table.put_item(Item=item)
            log_event(
                event_type="container_usage_recorded", 
                details={
                    "UserId": user_id, 
                    "ContainerId": container_id,
                    "MemoryLimit": memory_limit
                }
            )
            return True
            
        except ClientError as e:
            log_event(
                event_type="container_usage_record_failed", 
                details={"error": e.response['Error']['Message']}, 
                level="error", 
                error=e
            )
            return False

    def get_conversation_containers(self, conversation_id: str) -> list:
        """
        Retrieves all container records for a specific conversation using the ConversationIndex.
        Useful for checking if we have already billed for a container in this conversation.
        """
        try:
            response = self.table.query(
                IndexName='ConversationIndex', 
                KeyConditionExpression=boto3.dynamodb.conditions.Key('ConversationId').eq(conversation_id)
            )
            return response.get('Items', [])
            
        except ClientError as e:
            log_event(
                event_type="container_usage_retrieve_failed", 
                details={"ConversationId": conversation_id, "error": e.response['Error']['Message']}, 
                level="error", 
                error=e
            )
            return []