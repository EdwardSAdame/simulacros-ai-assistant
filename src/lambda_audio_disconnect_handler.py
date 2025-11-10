import json
import logging
from src.storage.ws_audio_table import WsAudioTable  # <-- UPDATED IMPORT

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Handles WebSocket disconnections for the AUDIO stream.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')
    if not connection_id:
        logger.error("No connectionId in $disconnect event")
        return {'statusCode': 400, 'body': 'connectionId not found.'}

    logger.info(f"AUDIO $disconnect event for connectionId: {connection_id}")

    try:
        table = WsAudioTable()  # <-- USE NEW CLASS
        table.delete_connection(connection_id)
        return {'statusCode': 200, 'body': 'Disconnected.'}
    except Exception as e:
        logger.error(f"Failed to delete AUDIO connection {connection_id}: {e}")
        return {'statusCode': 500, 'body': 'Disconnection failed.'}