# src/storage/ws_connections_table.py
import boto3
import os

TABLE_NAME = os.environ.get('WEBSOCKET_TABLE_NAME')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def save_connection(connection_id: str):
    """
    Saves a new WebSocket connection ID to the table.
    """
    if not connection_id:
        raise ValueError("connectionId cannot be empty")
    
    table.put_item(Item={'connectionId': connection_id})

def delete_connection(connection_id: str):
    """
    Deletes a WebSocket connection ID from the table.
    """
    if not connection_id:
        raise ValueError("connectionId cannot be empty")
        
    table.delete_item(Key={'connectionId': connection_id})