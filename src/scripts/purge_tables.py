# src/scripts/purge_tables.py
import boto3
import os # Import the os module

# --- Configuration ---
# List of your DynamoDB table names to be purged
TABLE_NAMES = [
    "UserConversations",
    "ConversationMessages",
    "MessageFeedback",
    "WsConnections"
]

# --- FIX: Explicitly define the AWS region ---
AWS_REGION = "us-east-1"

def purge_table(table_name: str):
    """
    Scans a DynamoDB table and deletes all items within it.
    """
    try:
        # Pass the region directly when creating the resource
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        table = dynamodb.Table(table_name)
        
        # Determine the primary key(s) of the table
        key_names = [key['AttributeName'] for key in table.key_schema]

        # Use batch_writer for efficient deletion
        with table.batch_writer() as batch:
            # Scan the table to get all items.
            # This handles pagination for large tables automatically.
            scan_kwargs = {}
            data = []
            done = False
            while not done:
                response = table.scan(**scan_kwargs)
                data.extend(response.get('Items', []))
                start_key = response.get('LastEvaluatedKey', None)
                scan_kwargs['ExclusiveStartKey'] = start_key
                done = start_key is None

            if not data:
                print(f"Table '{table_name}' is already empty.")
                return

            print(f"Found {len(data)} items to delete from '{table_name}'...")

            for item in data:
                # Construct the key for the delete operation
                key_to_delete = {k: item[k] for k in key_names}
                batch.delete_item(Key=key_to_delete)
        
        print(f"✅ Successfully purged all items from table '{table_name}'.")

    except Exception as e:
        print(f"❌ Error purging table '{table_name}': {e}")

if __name__ == "__main__":
    print("--- Starting DynamoDB Table Purge ---")
    print("WARNING: This action is irreversible and will delete all data from the specified tables.")
    
    confirm = input("Are you sure you want to continue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        for name in TABLE_NAMES:
            purge_table(name)
        print("\n--- Purge process complete. ---")
    else:
        print("\nOperation cancelled.")