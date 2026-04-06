# src/storage/image_usage_table.py
import boto3
import logging
from typing import Dict, Any, List
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

class ImageUsageTable:
    """
    Data Access Layer for the ImageUsage DynamoDB table.
    Handles raw database operations and GSI queries.
    """
    def __init__(self):
        # Initialize DynamoDB Resource
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table('ImageUsage')

    def put_item(self, item: Dict[str, Any]) -> bool:
        """
        Saves a completely formatted image usage record to DynamoDB.
        """
        try:
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"DynamoDB Error saving image usage: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving image usage: {e}")
            return False

    def get_by_user(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Queries image usage for a specific user using the GSI.
        Returns the newest records first.
        """
        try:
            response = self.table.query(
                IndexName='UserId-Timestamp-index',
                KeyConditionExpression=Key('UserId').eq(user_id),
                ScanIndexForward=False,  # Set to False to get newest timestamps first
                Limit=limit
            )
            return response.get('Items', [])
        except ClientError as e:
            logger.error(f"DynamoDB Error querying image usage for user {user_id}: {e.response['Error']['Message']}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying image usage for user {user_id}: {e}")
            return []

# Optional: Expose a singleton instance if you prefer that pattern
image_usage_table = ImageUsageTable()