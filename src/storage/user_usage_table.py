import os
import time
import boto3
from botocore.exceptions import ClientError
from src.utils.logging_utils import log_event

class UserUsageTable:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('USER_USAGE_TABLE_NAME', 'UserUsage')
        self.table = self.dynamodb.Table(self.table_name)

    def get_usage(self, user_id: str, window_duration: int) -> dict:
        """
        Retrieves the user's current usage counts. 
        If the window is expired or missing, returns a normalized zero-state dictionary.
        """
        current_time = int(time.time())
        try:
            response = self.table.get_item(Key={'UserId': user_id})
            item = response.get('Item')

            if not item or item.get('ExpiresAt', 0) <= current_time:
                return {
                    'UserId': user_id,
                    'StandardTextCount': 0,
                    'HighComputeCount': 0,
                    'VoiceCount': 0,
                    'WindowStartTime': current_time,
                    'ExpiresAt': current_time + window_duration
                }
            return item

        except ClientError as e:
            log_event(
                event_type="user_usage_retrieve_failed",
                details={"UserId": user_id, "error": e.response['Error']['Message']},
                level="error",
                error=e
            )
            return None

    def increment_usage(self, user_id: str, usage_type, window_duration: int) -> dict:
        """
        Atomically increments the appropriate bucket if the fixed window is still valid.
        If the window has expired or the user is new, it catches the condition failure 
        and safely initializes a new tracking window.
        """
        current_time = int(time.time())
        
        # Determine the target attribute based on the usage type
        # Fallback to boolean check safely handles legacy calls (is_high_compute)
        if isinstance(usage_type, bool):
            count_attribute = 'HighComputeCount' if usage_type else 'StandardTextCount'
        elif usage_type == "voice":
            count_attribute = 'VoiceCount'
        elif usage_type == "high_compute":
            count_attribute = 'HighComputeCount'
        else:
            count_attribute = 'StandardTextCount'

        try:
            # Atomic update: Adds 1 directly in the database to prevent race conditions
            response = self.table.update_item(
                Key={'UserId': user_id},
                UpdateExpression=f"ADD {count_attribute} :inc",
                ConditionExpression="attribute_exists(UserId) AND ExpiresAt > :now",
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':now': current_time
                },
                ReturnValues="ALL_NEW"
            )
            return response.get('Attributes')

        except ClientError as e:
            # If the condition fails, the window expired or the user does not exist yet
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                expires_at = current_time + window_duration
                new_item = {
                    'UserId': user_id,
                    'StandardTextCount': 0,
                    'HighComputeCount': 0,
                    'VoiceCount': 0,
                    'WindowStartTime': current_time,
                    'ExpiresAt': expires_at
                }
                
                # Apply the first count to the fresh window
                new_item[count_attribute] = 1

                try:
                    self.table.put_item(Item=new_item)
                    return new_item
                except ClientError as put_error:
                    log_event(
                        event_type="user_usage_reset_failed",
                        details={"UserId": user_id, "error": put_error.response['Error']['Message']},
                        level="error",
                        error=put_error
                    )
                    return None
            else:
                log_event(
                    event_type="user_usage_increment_failed",
                    details={"UserId": user_id, "error": e.response['Error']['Message']},
                    level="error",
                    error=e
                )
                return None