import os
import boto3
from botocore.exceptions import ClientError
import logging
import uuid
from datetime import datetime, timezone
from src.config.settings import settings # We will add the table name to settings next

logger = logging.getLogger(__name__)

class AudioUsageTable:
    def __init__(self):
        self.table_name = settings.AUDIO_USAGE_TABLE_NAME
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(self.table_name)

    def log_audio_usage(self, user_id: str, conversation_id: str, source: str, tier: str, engine: str, duration_seconds: int, audio_type: str = "speech-to-text"):
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            item = {
                'UsageId': str(uuid.uuid4()),
                'UserId': user_id,
                'Timestamp': timestamp,
                'Engine': engine,
                'DurationSeconds': duration_seconds,
                'Metadata': {
                    'ConversationId': conversation_id,
                    'Tier': tier,
                    'Source': source,
                    'AudioType': audio_type
                }
            }
            
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"Failed to log audio usage: {e}")
            return False