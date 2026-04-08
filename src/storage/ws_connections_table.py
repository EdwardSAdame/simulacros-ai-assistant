# src/storage/ws_connections_table.py
import os
import boto3
import logging
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)

class WsConnectionsTable:
    def __init__(self, table_name: str = None):
        self.dynamodb = boto3.resource('dynamodb')
        
        # If the Lambda handler doesn't pass a name, use the environment variable or default to 'WsConnections'
        actual_table_name = table_name or os.environ.get('TABLE_NAME') or os.environ.get('WS_CONNECTIONS_TABLE_NAME') or 'WsConnections'
        
        self.table = self.dynamodb.Table(actual_table_name)

    # 🟢 THE FIX: Renamed from 'save_connection' to 'add_connection' to match your Lambda handler
    def add_connection(self, user_id: str, connection_id: str):
        """
        Saves a new WebSocket connection ID for the user using a DynamoDB String Set.
        """
        try:
            self.table.update_item(
                Key={'userId': user_id},
                UpdateExpression="ADD connectionIds :c",
                ExpressionAttributeValues={":c": set([connection_id])}
            )
            logger.info(f"Saved connection {connection_id} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save connection: {e}")
            raise

    def get_connection_ids(self, user_id: str) -> list:
        """
        Retrieves all active WebSocket connection IDs for the user.
        """
        try:
            response = self.table.get_item(Key={'userId': user_id})
            item = response.get('Item', {})
            # DynamoDB returns sets as Python sets. We convert back to a list for JSON serialization.
            connections = item.get('connectionIds', set())
            return list(connections)
        except Exception as e:
            logger.error(f"Failed to get connections for user {user_id}: {e}")
            return []

    def remove_connection_by_id(self, connection_id: str):
        """
        Removes a connection using the connectionId from the String Set.
        If it was the user's last connection, it deletes the entire user row to keep the database clean.
        """
        if not connection_id:
            logger.warning("remove_connection_by_id failed: connection_id is empty.")
            raise ValueError("connectionId cannot be empty")
            
        try:
            # Step 1: Scan to find which user owns this connectionId
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
                
                # Step 2: Remove the specific connection ID AND ask DynamoDB to return the remaining attributes
                update_response = self.table.update_item(
                    Key={'userId': user_id},
                    UpdateExpression="DELETE connectionIds :c",
                    ExpressionAttributeValues={":c": set([connection_id])},
                    ReturnValues="UPDATED_NEW" 
                )
                
                # Step 3: Check if the set is empty/missing. If so, delete the zombie row entirely.
                remaining_attributes = update_response.get('Attributes', {})
                if 'connectionIds' not in remaining_attributes or not remaining_attributes['connectionIds']:
                    logger.info(f"User {user_id} has no more connections. Deleting row to save space.")
                    self.table.delete_item(Key={'userId': user_id})
                    
        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {str(e)}")