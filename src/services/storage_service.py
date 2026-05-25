# src/services/storage_service.py
import boto3
import logging
import uuid
from botocore.exceptions import ClientError
from src.config.settings import settings

# IMPORT CUSTOM LOGGING
from src.utils.logging_utils import log_event

logger = logging.getLogger(__name__)

class StorageService:
    """
    Handles private file uploads to AWS S3, routing between Dynamic AI Assets and Static Exam Assets.
    """
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)

    # ---------------------------------------------------------
    # 1. ACTIVE AI GENERATION (Chat, Quizzes, Flashcards)
    # ---------------------------------------------------------
    def upload_image_from_bytes(self, file_content: bytes, content_type: str = "image/png", folder: str = "quiz_assets") -> str:
        """
        Uploads dynamic AI images to the AI_ASSETS_BUCKET.
        NOTE: Retained original function name so existing AI services do not break.
        """
        # 1. Determine Extension
        file_extension = ".png"
        if "jpeg" in content_type or "jpg" in content_type:
            file_extension = ".jpg"
        elif "pdf" in content_type:
            file_extension = ".pdf"
            
        # 2. Generate a unique filename
        file_name = f"{folder}/{uuid.uuid4()}{file_extension}"
        bucket = settings.AI_ASSETS_BUCKET
        
        try:
            # 3. Upload to S3
            self.s3_client.put_object(
                Bucket=bucket,
                Key=file_name,
                Body=file_content,
                ContentType=content_type
            )
            
            # 4. Construct URL (Use AI CDN if configured, else fallback to standard S3 URL)
            if hasattr(settings, 'AI_ASSETS_CDN') and settings.AI_ASSETS_CDN:
                url = f"https://{settings.AI_ASSETS_CDN}/{file_name}"
            else:
                url = f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
                
            # STRUCTURED LOGGING
            log_event("ai_asset_uploaded", {
                "url": url,
                "folder": folder,
                "file_name": file_name,
                "content_type": content_type,
                "bucket": bucket
            })
            
            return url

        except ClientError as e:
            log_event("ai_asset_upload_failed", {
                "folder": folder,
                "file_name": file_name,
                "content_type": content_type,
                "bucket": bucket
            }, level="error", error=str(e))
            raise e

    # ---------------------------------------------------------
    # 2. NEW MOCK EXAM CDN (Static Assets)
    # ---------------------------------------------------------
    def upload_exam_asset(self, file_content: bytes, content_type: str = "image/png", folder: str = "exam_assets") -> str:
        """
        Uploads static mock exam images directly to the secure CloudFront CDN bucket.
        """
        # 1. Determine Extension
        file_extension = ".png"
        if "jpeg" in content_type or "jpg" in content_type:
            file_extension = ".jpg"
        elif "pdf" in content_type:
            file_extension = ".pdf"
            
        # 2. Generate a unique filename
        file_name = f"{folder}/{uuid.uuid4()}{file_extension}"
        bucket = settings.CDN_ASSETS_BUCKET
        
        try:
            # 3. Upload to S3
            self.s3_client.put_object(
                Bucket=bucket,
                Key=file_name,
                Body=file_content,
                ContentType=content_type
            )
            
            # 4. Construct the ultra-fast CloudFront CDN URL
            if hasattr(settings, 'CDN_CUSTOM_DOMAIN') and settings.CDN_CUSTOM_DOMAIN:
                url = f"https://{settings.CDN_CUSTOM_DOMAIN}/{file_name}"
            else:
                url = f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
                
            # STRUCTURED LOGGING
            log_event("exam_asset_uploaded", {
                "url": url,
                "folder": folder,
                "file_name": file_name,
                "content_type": content_type,
                "bucket": bucket
            })
            
            return url

        except ClientError as e:
            log_event("exam_asset_upload_failed", {
                "folder": folder,
                "file_name": file_name,
                "content_type": content_type,
                "bucket": bucket
            }, level="error", error=str(e))
            raise e

# Create a singleton instance to be imported elsewhere
storage_service = StorageService()