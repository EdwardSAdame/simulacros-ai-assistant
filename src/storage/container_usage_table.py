# src/storage/container_usage_table.py
import os
import boto3
from decimal import Decimal
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
        session_id: str, 
        container_id: str, 
        memory_limit: str, 
        estimated_cost: float
    ) -> bool:
        """
        Saves a single container usage record to DynamoDB.
        Uses PascalCase for database keys to match conventions.
        """
        try:
            item = {
                'UserId': user_id,
                'Timestamp': timestamp,
                'SessionId': session_id,
                'ContainerId': container_id,
                'MemoryLimit': memory_limit,
                # DynamoDB requires floats to be cast to Decimal
                'EstimatedCost': Decimal(str(estimated_cost)) 
            }
            
            self.table.put_item(Item=item)
            log_event(
                event_type="container_usage_recorded", 
                details={
                    "UserId": user_id, 
                    "ContainerId": container_id, 
                    "EstimatedCost": estimated_cost
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

    def get_session_containers(self, session_id: str) -> list:
        """
        Retrieves all container records for a specific session using the SessionIndex.
        Useful for checking if we have already billed for a container in this session.
        """
        try:
            response = self.table.query(
                IndexName='SessionIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('SessionId').eq(session_id)
            )
            return response.get('Items', [])
            
        except ClientError as e:
            log_event(
                event_type="container_usage_session_retrieve_failed", 
                details={"SessionId": session_id, "error": e.response['Error']['Message']}, 
                level="error", 
                error=e
            )
            return []