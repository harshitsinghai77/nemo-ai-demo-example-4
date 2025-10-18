import boto3
import io
import os
from datetime import datetime
from typing import Optional
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

logger = Logger()


class S3Service:
    """
    Service for handling S3 operations for CSV file storage.
    
    This service manages uploading CSV files to the configured S3 bucket
    with proper naming conventions and metadata.
    """
    
    def __init__(self):
        """Initialize S3 service with boto3 client and bucket configuration."""
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ.get('S3_BUCKET_NAME')
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable not set")
    
    def upload_csv_file(self, file_content: bytes, filename: str) -> str:
        """
        Upload CSV file to S3 bucket with timestamp-based filename.
        
        Args:
            file_content: Raw file content bytes
            filename: Original filename for reference
            
        Returns:
            S3 object key of uploaded file
            
        Raises:
            Exception: If upload fails
        """
        try:
            # Generate timestamp-based filename as per requirements
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            s3_key = f"user_data_{timestamp}.csv"
            
            # Create file-like object from bytes
            file_obj = io.BytesIO(file_content)
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'text/csv',
                    'Metadata': {
                        'original_filename': filename,
                        'upload_timestamp': timestamp,
                        'content_length': str(len(file_content))
                    }
                }
            )
            
            logger.info(f"Successfully uploaded CSV file to S3: {s3_key}")
            return s3_key
            
        except ClientError as e:
            error_msg = f"Failed to upload file to S3: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during S3 upload: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def check_bucket_exists(self) -> bool:
        """
        Check if the configured S3 bucket exists and is accessible.
        
        Returns:
            True if bucket exists and is accessible, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False