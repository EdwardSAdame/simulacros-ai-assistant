import boto3
import logging
from typing import Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class VectorStoreTable:
    """
    Data access layer for the ExamVectorStores DynamoDB table.
    """
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('ExamVectorStores')

    def get_vector_store_id(self, exam_id: str) -> Optional[str]:
        """
        Retrieves the OpenAI vector store ID for a given exam identifier.
        """
        try:
            response = self.table.get_item(Key={'ExamId': exam_id})
            item = response.get('Item')
            
            if item and 'VectorStoreId' in item:
                return item['VectorStoreId']
                
            return None
            
        except ClientError as e:
            logger.error(f"DynamoDB ClientError retrieving vector store ID for {exam_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving vector store ID for {exam_id}: {e}")
            return None