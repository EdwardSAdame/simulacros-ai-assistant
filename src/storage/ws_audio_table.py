import boto3
from botocore.exceptions import ClientError
from src.config.settings import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)

class WsAudioTable:  # <-- RENAMED CLASS
    """
    Handles operations for the DynamoDB table that stores active WebSocket
    connection IDs for the AUDIO stream (WsAudio table).
    """
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = settings.WS_AUDIO_TABLE_NAME  # <-- USES NEW SETTING
        self.table = self.dynamodb.Table(self.table_name)

    def save_connection(self, connection_id: str):
        """
        Saves a new connection ID to the table.
        """
        try:
            self.table.put_item(Item={'connectionId': connection_id})
            logger.info(f"AUDIO Connection saved: {connection_id} to {self.table_name}")
        except ClientError as e:
            logger.error(f"Error saving AUDIO connection {connection_id}: {e}")
            raise

    def delete_connection(self, connection_id: str):
        """
        Deletes a connection ID from the table.
        """
        try:
            self.table.delete_item(Key={'connectionId': connection_id})
            logger.info(f"AUDIO Connection deleted: {connection_id} from {self.table_name}")
        except ClientError as e:
            logger.error(f"Error deleting AUDIO connection {connection_id}: {e}")
            raise