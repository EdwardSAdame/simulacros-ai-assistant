# src/storage/ws_connections_table.py
import boto3
import logging
import os

logger = logging.getLogger()

# --- Best Practice: Initialize the client once ---
dynamodb = boto3.resource('dynamodb')

# --- Use a more descriptive name for the table from environment variables ---
TABLE_NAME = os.environ.get('WEBSOCKET_CONNECTIONS_TABLE_NAME', 'WsConnections') 
# Note: I've added a default table name 'WsConnections' for clarity.
# You will need to create a DynamoDB table with this name and 'userId' as the primary key.

class WsConnectionsTable:
    """Manages WebSocket connections in a DynamoDB table."""

    def __init__(self):
        """Initializes the table resource."""
        self.table = dynamodb.Table(TABLE_NAME)

    def add_connection(self, user_id: str, connection_id: str):
        """
        Saves or updates a user's connection ID.
        Uses userId as the primary key.
        """
        if not user_id or not connection_id:
            logger.warning("add_connection failed: userId or connection_id is empty.")
            raise ValueError("userId and connectionId cannot be empty")

        logger.info(f"Storing connection for userId: {user_id}")
        self.table.put_item(
            Item={
                'userId': user_id,
                'connectionId': connection_id
            }
        )

    def remove_connection_by_id(self, connection_id: str):
        """
        Removes a connection using the connectionId.
        This requires a scan, which is less efficient but necessary if only
        the connectionId is available on disconnect.
        """
        if not connection_id:
            logger.warning("remove_connection_by_id failed: connection_id is empty.")
            raise ValueError("connectionId cannot be empty")
            
        # Scan the table to find the item with the matching connectionId
        response = self.table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('connectionId').eq(connection_id)
        )
        
        items = response.get('Items', [])
        if items:
            user_id = items[0]['userId']
            logger.info(f"Removing connection for userId: {user_id} with connectionId: {connection_id}")
            self.table.delete_item(Key={'userId': user_id})
        else:
            logger.warning(f"No connection found with connectionId: {connection_id} to remove.")

    def get_connection_id(self, user_id: str) -> str | None:
        """
        Retrieves a connection ID for a given user ID.
        """
        if not user_id:
            logger.warning("get_connection_id failed: userId is empty.")
            return None

        logger.info(f"Fetching connection for userId: {user_id}")
        try:
            response = self.table.get_item(Key={'userId': user_id})
            item = response.get('Item')
            return item['connectionId'] if item else None
        except Exception as e:
            logger.error(f"Error getting connection for {user_id}: {e}")
            return None