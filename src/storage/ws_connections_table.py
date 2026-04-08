# src/storage/ws_connections_table.py
import boto3
import logging
import os
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger()

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('WEBSOCKET_CONNECTIONS_TABLE_NAME', 'WsConnections')

class WsConnectionsTable:
    """Manages WebSocket connections in a DynamoDB table, supporting multiple connections per user."""

    def __init__(self):
        """Initializes the table resource."""
        self.table = dynamodb.Table(TABLE_NAME)

    def add_connection(self, user_id: str, connection_id: str):
        """
        Saves or updates a user's connection ID using a DynamoDB String Set.
        This allows one user to have multiple active browser windows (connections).
        """
        if not user_id or not connection_id:
            logger.warning("add_connection failed: userId or connection_id is empty.")
            raise ValueError("userId and connectionId cannot be empty")

        logger.info(f"Storing connection {connection_id} for userId: {user_id}")
        
        try:
            self.table.update_item(
                Key={'userId': user_id},
                UpdateExpression="ADD connectionIds :c",
                ExpressionAttributeValues={":c": set([connection_id])}
            )
        except Exception as e:
            logger.error(f"Failed to add connection {connection_id} for {user_id}: {str(e)}")
            raise e

    def remove_connection_by_id(self, connection_id: str):
        """
        Removes a connection using the connectionId from the String Set.
        Uses a scan to find the user first, then removes the specific connection ID.
        """
        if not connection_id:
            logger.warning("remove_connection_by_id failed: connection_id is empty.")
            raise ValueError("connectionId cannot be empty")
            
        try:
            response = self.table.scan(
                FilterExpression=Attr('connectionIds').contains(connection_id)
            )
            
            items = response.get('Items', [])
            if not items:
                logger.warning(f"No user found owning connectionId: {connection_id} to remove.")
                return

            for item in items:
                user_id = item['userId']
                logger.info(f"Removing connection {connection_id} from userId: {user_id}")
                
                self.table.update_item(
                    Key={'userId': user_id},
                    UpdateExpression="DELETE connectionIds :c",
                    ExpressionAttributeValues={":c": set([connection_id])}
                )
        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {str(e)}")

    def get_connection_ids(self, user_id: str) -> list:
        """
        Retrieves all active connection IDs for a given user ID.
        Returns an empty list if none are found.
        """
        if not user_id:
            logger.warning("get_connection_ids failed: userId is empty.")
            return []

        logger.info(f"Fetching connections for userId: {user_id}")
        try:
            response = self.table.get_item(Key={'userId': user_id})
            item = response.get('Item')
            
            if item and 'connectionIds' in item:
                return list(item['connectionIds'])
            return []
        except Exception as e:
            logger.error(f"Error getting connections for {user_id}: {str(e)}")
            return []