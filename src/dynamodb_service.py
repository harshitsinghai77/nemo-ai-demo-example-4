import boto3
import os
import uuid
from typing import List, Dict, Any
from datetime import datetime
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

logger = Logger()


class DynamoDBService:
    """
    Service for handling DynamoDB operations for user data storage.
    
    This service manages writing CSV data to the configured DynamoDB table
    with UUID generation and batch operations for efficiency.
    """
    
    def __init__(self):
        """Initialize DynamoDB service with boto3 resource and table configuration."""
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('DYNAMODB_TABLE_NAME')
        
        if not self.table_name:
            raise ValueError("DYNAMODB_TABLE_NAME environment variable not set")
        
        self.table = self.dynamodb.Table(self.table_name)
    
    def write_csv_data(self, csv_rows: List[Dict[str, str]], s3_file_key: str) -> int:
        """
        Write CSV data to DynamoDB table with UUID primary keys.
        
        Args:
            csv_rows: List of dictionaries containing user data
            s3_file_key: S3 key of the source CSV file for tracking
            
        Returns:
            Number of records successfully written
            
        Raises:
            Exception: If batch write fails
        """
        if not csv_rows:
            return 0
        
        try:
            records_written = 0
            timestamp = datetime.now().isoformat()
            
            # Use batch writer for efficient bulk writes
            with self.table.batch_writer() as batch:
                for row in csv_rows:
                    # Generate UUID for entry_id (primary key)
                    entry_id = str(uuid.uuid4())
                    
                    # Prepare item for DynamoDB
                    item = {
                        'entry_id': entry_id,  # Primary key
                        'source_file': s3_file_key,  # Track source file
                        'created_at': timestamp,  # Track creation time
                    }
                    
                    # Add all user data fields (only non-empty values)
                    for field, value in row.items():
                        if value and value.strip():  # Only add non-empty values
                            item[field] = value.strip()
                    
                    # Write to DynamoDB
                    batch.put_item(Item=item)
                    records_written += 1
            
            logger.info(f"Successfully wrote {records_written} records to DynamoDB table: {self.table_name}")
            return records_written
            
        except ClientError as e:
            error_msg = f"Failed to write data to DynamoDB: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during DynamoDB write: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def check_table_exists(self) -> bool:
        """
        Check if the configured DynamoDB table exists and is accessible.
        
        Returns:
            True if table exists and is accessible, False otherwise
        """
        try:
            self.table.load()
            return self.table.table_status == 'ACTIVE'
        except ClientError:
            return False
        except Exception:
            return False
    
    def get_table_item_count(self) -> int:
        """
        Get the approximate number of items in the table (for monitoring).
        
        Returns:
            Approximate item count, or -1 if unable to retrieve
        """
        try:
            self.table.reload()
            return self.table.item_count or 0
        except Exception:
            return -1