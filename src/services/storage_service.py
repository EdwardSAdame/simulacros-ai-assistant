import boto3
import logging
import uuid
from botocore.exceptions import ClientError
from src.config.settings import settings

logger = logging.getLogger(__name__)

class StorageService:
    """
    Handles file uploads to AWS S3.
    """
    def __init__(self):
        # We allow the region to be configurable via settings
        self.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
        self.bucket_name = settings.S3_BUCKET_NAME

    def upload_image_from_bytes(self, file_content: bytes, content_type: str = "image/png", folder: str = "quiz_assets") -> str:
        """
        Uploads raw image bytes to S3 and returns the public URL.
        Generates a unique filename using UUID to prevent collisions.
        
        Args:
            file_content (bytes): The raw binary data of the image.
            content_type (str): The MIME type (default: image/png).
            folder (str): The folder (prefix) inside the bucket. Default: 'quiz_assets'.
            
        Returns:
            str: The public HTTPS URL of the uploaded image.
        """
        # 1. Determine Extension
        file_extension = ".png"
        if "jpeg" in content_type:
            file_extension = ".jpg"
        elif "pdf" in content_type:
            file_extension = ".pdf"
            
        # 2. Generate a unique filename using the provided folder
        # 🟢 FIX: Dynamic folder selection (chat_assets vs quiz_assets)
        file_name = f"{folder}/{uuid.uuid4()}{file_extension}"
        
        try:
            # 3. Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_content,
                ContentType=content_type
                # ACL='public-read' # Uncomment if your bucket isn't using Policy-based public access
            )
            
            # 4. Construct the Public URL
            if hasattr(settings, 'S3_CUSTOM_DOMAIN') and settings.S3_CUSTOM_DOMAIN:
                # If you use CloudFront later
                url = f"https://{settings.S3_CUSTOM_DOMAIN}/{file_name}"
            else:
                # Standard S3 URL
                url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
                
            logger.info(f"StorageService: Successfully uploaded image to {url}")
            return url

        except ClientError as e:
            logger.error(f"StorageService: S3 Upload failed: {e}")
            raise e

# Create a singleton instance to be imported elsewhere
storage_service = StorageService()