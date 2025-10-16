import pytest
import sys
import os
import json
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from csv_processor import validate_csv_file, parse_csv_content, extract_valid_rows
from models import UserDataRow, CSVPreviewResponse, CSVUploadResponse


class TestCSVProcessor:
    """Test CSV processing functionality"""
    
    def test_validate_csv_file_valid(self):
        """Test CSV validation with valid file"""
        csv_content = b"user_id,name,email\n1,John Doe,john@example.com\n2,Jane Smith,jane@example.com"
        is_valid, error = validate_csv_file(csv_content, "test.csv")
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_csv_file_invalid_extension(self):
        """Test CSV validation with invalid file extension"""
        csv_content = b"user_id,name,email\n1,John,john@test.com"
        is_valid, error = validate_csv_file(csv_content, "test.txt")
        
        assert is_valid is False
        assert "Only .csv files are accepted" in error
    
    def test_validate_csv_file_too_large(self):
        """Test CSV validation with file too large"""
        # Create content larger than 5MB
        large_content = b"user_id,name,email\n" + b"1,John,john@test.com\n" * 500000
        is_valid, error = validate_csv_file(large_content, "test.csv")
        
        assert is_valid is False
        assert "File size exceeds 5MB limit" in error
    
    def test_parse_csv_content_valid(self):
        """Test parsing valid CSV content"""
        csv_content = b"user_id,name,email,phone_number\n1,John Doe,john@example.com,123-456-7890\n2,Jane Smith,jane@example.com,"
        
        result = parse_csv_content(csv_content)
        
        assert result.status == "success"
        assert result.total_rows == 2
        assert result.valid_rows == 2
        assert "user_id" in result.valid_columns
        assert "name" in result.valid_columns
        assert "email" in result.valid_columns
        assert "phone_number" in result.valid_columns
    
    def test_parse_csv_content_no_valid_columns(self):
        """Test parsing CSV with no valid columns"""
        csv_content = b"invalid_col1,invalid_col2\nvalue1,value2\nvalue3,value4"
        
        result = parse_csv_content(csv_content)
        
        assert result.status == "error"
        assert result.total_rows == 0
        assert result.valid_rows == 0
        assert len(result.valid_columns) == 0
        assert "No valid columns found" in result.message
    
    def test_parse_csv_content_mixed_columns(self):
        """Test parsing CSV with both valid and invalid columns"""
        csv_content = b"user_id,name,invalid_col,email\n1,John,extra,john@test.com\n2,Jane,data,jane@test.com"
        
        result = parse_csv_content(csv_content)
        
        assert result.status == "success"
        assert result.total_rows == 2
        assert result.valid_rows == 2
        assert "user_id" in result.valid_columns
        assert "name" in result.valid_columns
        assert "email" in result.valid_columns
        assert "invalid_col" in result.invalid_columns
    
    # def test_extract_valid_rows(self):
    #     """Test extracting valid rows from CSV"""
    #     csv_content = b"user_id,name,email,country\n1,John Doe,john@example.com,USA\n2,Jane Smith,jane@example.com,Canada\n3,,,UK"
        
    #     rows = extract_valid_rows(csv_content)
        
    #     assert len(rows) == 2  # Third row should be excluded (only empty required fields)
    #     assert rows[0]["user_id"] == "1"
    #     assert rows[0]["name"] == "John Doe"
    #     assert rows[0]["email"] == "john@example.com"
    #     assert rows[0]["country"] == "USA"
        
    #     assert rows[1]["user_id"] == "2"
    #     assert rows[1]["name"] == "Jane Smith"


class TestModels:
    """Test Pydantic models"""
    
    def test_user_data_row_model(self):
        """Test UserDataRow model"""
        data = {
            "user_id": "123",
            "name": "John Doe", 
            "email": "john@example.com",
            "phone_number": "123-456-7890",
            "country": "USA"
        }
        
        user_row = UserDataRow(**data)
        assert user_row.user_id == "123"
        assert user_row.name == "John Doe"
        assert user_row.email == "john@example.com"
    
    def test_csv_preview_response_model(self):
        """Test CSVPreviewResponse model"""
        data = {
            "status": "success",
            "message": "Preview generated",
            "valid_columns": ["user_id", "name"],
            "invalid_columns": ["extra_col"],
            "total_rows": 10,
            "valid_rows": 8,
            "preview_data": [{"user_id": "1", "name": "John"}]
        }
        
        response = CSVPreviewResponse(**data)
        assert response.status == "success"
        assert len(response.valid_columns) == 2
        assert response.total_rows == 10
    
    def test_csv_upload_response_model(self):
        """Test CSVUploadResponse model"""
        data = {
            "status": "success",
            "message": "Upload completed",
            "s3_file_key": "user_data_2024-01-01_12-00-00.csv",
            "dynamodb_records_written": 15
        }
        
        response = CSVUploadResponse(**data)
        assert response.status == "success"
        assert response.s3_file_key == "user_data_2024-01-01_12-00-00.csv"
        assert response.dynamodb_records_written == 15


if __name__ == "__main__":
    # Run basic tests
    processor_tests = TestCSVProcessor()
    model_tests = TestModels()
    
    try:
        processor_tests.test_validate_csv_file_valid()
        processor_tests.test_validate_csv_file_invalid_extension() 
        processor_tests.test_parse_csv_content_valid()
        processor_tests.test_parse_csv_content_no_valid_columns()
        processor_tests.test_extract_valid_rows()
        
        model_tests.test_user_data_row_model()
        model_tests.test_csv_preview_response_model()
        model_tests.test_csv_upload_response_model()
        
        print("✅ All CSV functionality tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()