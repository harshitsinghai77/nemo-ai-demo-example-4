import csv
import io
from typing import List, Dict, Any, Tuple
from models import UserDataRow, CSVPreviewResponse


# Predefined columns as per Jira requirements
PREDEFINED_COLUMNS = {
    'user_id', 'name', 'email', 'phone_number', 'country', 
    'state', 'city', 'signup_date', 'last_active_date'
}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
MAX_PREVIEW_ROWS = 10  # Number of rows to show in preview


def validate_csv_file(file_content: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validate CSV file format and size.
    
    Args:
        file_content: Raw file content
        filename: Name of the uploaded file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file extension
    if not filename.lower().endswith('.csv'):
        return False, "Only .csv files are accepted"
    
    # Check file size
    if len(file_content) > MAX_FILE_SIZE_BYTES:
        return False, f"File size exceeds 5MB limit (current: {len(file_content)/1024/1024:.2f}MB)"
    
    # Try to decode as CSV
    try:
        content_str = file_content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(content_str))
        # Just read the first row to validate CSV format
        next(csv_reader)
        return True, ""
    except UnicodeDecodeError:
        return False, "File encoding not supported. Please use UTF-8 encoding"
    except csv.Error as e:
        return False, f"Invalid CSV format: {str(e)}"
    except StopIteration:
        return False, "Empty CSV file"
    except Exception as e:
        return False, f"Error processing CSV file: {str(e)}"


def parse_csv_content(file_content: bytes) -> CSVPreviewResponse:
    """
    Parse CSV content and return preview data with validation.
    
    Args:
        file_content: Raw CSV file content
        
    Returns:
        CSVPreviewResponse with parsed data and validation info
    """
    try:
        content_str = file_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))
        
        # Get headers
        headers = csv_reader.fieldnames or []
        
        # Identify valid and invalid columns using set operations for efficiency
        headers_set = set(headers)
        valid_columns = list(headers_set.intersection(PREDEFINED_COLUMNS))
        invalid_columns = list(headers_set.difference(PREDEFINED_COLUMNS))
        
        # Check if we have any valid columns
        if not valid_columns:
            return CSVPreviewResponse(
                status="error",
                message="No valid columns found",
                valid_columns=[],
                invalid_columns=invalid_columns,
                total_rows=0,
                valid_rows=0,
                preview_data=[],
                errors=["No valid columns found. Expected columns: " + ", ".join(PREDEFINED_COLUMNS)]
            )
        
        # Create column mapping for efficient lookup
        column_mapping = {col: col.lower() for col in headers if col.lower() in PREDEFINED_COLUMNS}
        
        # Parse rows in a single pass
        rows = []
        valid_rows = 0
        total_rows = 0
        errors = []
        preview_data = []
        
        for row_idx, row in enumerate(csv_reader):
            total_rows += 1
            
            # Extract only valid columns using the pre-computed mapping
            normalized_row = {}
            for original_col, normalized_key in column_mapping.items():
                normalized_row[normalized_key] = (row.get(original_col, "") or "").strip()
            
            try:
                # Validate row using Pydantic model
                user_row = UserDataRow(**normalized_row)
                valid_rows += 1
                
                # Add to preview data (limited number)
                if len(preview_data) < MAX_PREVIEW_ROWS:
                    # Convert back to dict for preview, keeping original column names for display
                    preview_row = {}
                    for original_col in valid_columns:
                        normalized_key = original_col.lower()
                        preview_row[original_col] = normalized_row.get(normalized_key, "")
                    preview_data.append(preview_row)
                    
            except Exception as e:
                errors.append(f"Row {row_idx + 2}: {str(e)}")  # +2 because of header and 0-based index
        
        status = "success" if valid_rows > 0 else "warning"
        message = f"Found {valid_rows} valid rows out of {total_rows} total rows"
        
        return CSVPreviewResponse(
            status=status,
            message=message,
            valid_columns=valid_columns,
            invalid_columns=invalid_columns,
            total_rows=total_rows,
            valid_rows=valid_rows,
            preview_data=preview_data,
            errors=errors[:10]  # Limit error messages
        )
        
    except Exception as e:
        return CSVPreviewResponse(
            status="error",
            message="Failed to parse CSV file",
            valid_columns=[],
            invalid_columns=[],
            total_rows=0,
            valid_rows=0,
            preview_data=[],
            errors=[f"Parse error: {str(e)}"]
        )


def extract_valid_rows(file_content: bytes) -> List[Dict[str, str]]:
    """
    Extract all valid rows from CSV content for DynamoDB insertion.
    
    Args:
        file_content: Raw CSV file content
        
    Returns:
        List of dictionaries with valid user data rows
    """
    try:
        content_str = file_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))
        
        headers = csv_reader.fieldnames or []
        valid_rows = []
        
        # Create column mapping for efficient lookup
        column_mapping = {col: col.lower() for col in headers if col.lower() in PREDEFINED_COLUMNS}
        
        for row in csv_reader:
            # Extract only valid columns using the pre-computed mapping
            normalized_row = {}
            for original_col, normalized_key in column_mapping.items():
                normalized_row[normalized_key] = (row.get(original_col, "") or "").strip()
            
            # Only include rows that have at least one non-empty field
            if any(value for value in normalized_row.values()):
                try:
                    # Validate using Pydantic model
                    UserDataRow(**normalized_row)
                    valid_rows.append(normalized_row)
                except Exception:
                    # Skip invalid rows
                    continue
        
        return valid_rows
        
    except Exception:
        return []