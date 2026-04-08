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
                    ReturnValues="UPDATED_NEW" # Tells DynamoDB to return what the row looks like now
                )
                
                # Step 3: Check if the set is empty/missing. If so, delete the zombie row entirely.
                remaining_attributes = update_response.get('Attributes', {})
                if 'connectionIds' not in remaining_attributes or not remaining_attributes['connectionIds']:
                    logger.info(f"User {user_id} has no more connections. Deleting row to save space.")
                    self.table.delete_item(Key={'userId': user_id})
                    
        except Exception as e:
            logger.error(f"Error removing connection {connection_id}: {str(e)}")