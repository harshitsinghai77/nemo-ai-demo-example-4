import json
import base64
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
from aws_lambda_powertools.event_handler import LambdaFunctionUrlResolver, Response, content_types
from aws_lambda_powertools.utilities.typing import LambdaContext
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from models import (
    PingResponse, HelloResponse, StatusResponse, User, 
    CreateUserRequest, CreateUserResponse, ErrorResponse,
    CSVPreviewResponse, CSVUploadResponse
)
from csv_processor import validate_csv_file, parse_csv_content, extract_valid_rows
from s3_service import S3Service
from dynamodb_service import DynamoDBService

app = LambdaFunctionUrlResolver()

# Initialize Jinja2 environment
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(['html', 'xml'])
)

# Initialize services
try:
    s3_service = S3Service()
    dynamodb_service = DynamoDBService()
except Exception as e:
    print(f"Warning: Failed to initialize AWS services: {e}")
    s3_service = None
    dynamodb_service = None
# Mock data for demo
MOCK_USERS = {
    "1": User(
        id="1",
        name="John Doe",
        email="john@example.com",
        active=True,
        created_at=(datetime.now() - timedelta(days=30)).isoformat(),
        recent_activity=["Logged in", "Updated profile", "Viewed dashboard"]
    ),
    "2": User(
        id="2",
        name="Jane Smith",
        email="jane@example.com",
        active=True,
        created_at=(datetime.now() - timedelta(days=15)).isoformat(),
        recent_activity=["Created account", "Completed onboarding"]
    )
}


@app.get("/")
def index() -> Response:
    """API documentation homepage"""
    template = jinja_env.get_template('index.html')
    html_content = template.render()
    
    return Response(
        status_code=200,
        content_type=content_types.TEXT_HTML,
        body=html_content
    )


@app.get("/ping")
def ping() -> Dict[str, Any]:
    """Health check endpoint"""
    response = PingResponse(message="pong", status="healthy")
    return response.model_dump()


@app.get("/hello")
def hello() -> Dict[str, Any]:
    """Hello world endpoint"""
    name = app.current_event.query_string_parameters.get("name") if app.current_event.query_string_parameters else None
    
    if name:
        message = f"Hello, {name}!"
    else:
        message = "Hello, World!"
    
    response = HelloResponse(message=message, name=name)
    return response.model_dump()


@app.get("/status")
def status() -> Dict[str, Any]:
    """Detailed system status endpoint"""
    response = StatusResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        uptime="Running",
        environment=os.environ.get("ENVIRONMENT", "production")
    )
    return response.model_dump()


@app.get("/users/<user_id>")
def get_user(user_id: str) -> Any:
    """Get user by ID - supports both JSON and HTML responses"""
    
    # Check Accept header for response format
    accept_header = app.current_event.headers.get("accept", "")
    wants_html = "text/html" in accept_header
    
    if user_id not in MOCK_USERS:
        if wants_html:
            return Response(
                status_code=404,
                content_type=content_types.TEXT_HTML,
                body="<h1>User Not Found</h1><p>The requested user does not exist.</p>"
            )
        else:
            error_response = ErrorResponse(error="NotFound", message="User not found")
            return Response(
                status_code=404,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
    
    user = MOCK_USERS[user_id]
    
    if wants_html:
        template = jinja_env.get_template('user_profile.html')
        html_content = template.render(user=user)
        return Response(
            status_code=200,
            content_type=content_types.TEXT_HTML,
            body=html_content
        )
    else:
        return user.model_dump()


@app.post("/users")
def create_user() -> Dict[str, Any]:
    """Create a new user"""
    
    try:
        # Parse request body
        request_data = CreateUserRequest.model_validate(app.current_event.json_body)
        
        # Generate new user ID
        new_user_id = str(len(MOCK_USERS) + 1)
        
        # Create new user
        new_user = User(
            id=new_user_id,
            name=request_data.name,
            email=request_data.email,
            active=True,
            created_at=datetime.now().isoformat(),
            recent_activity=["Account created"]
        )
        
        # Add to mock storage
        MOCK_USERS[new_user_id] = new_user
        
        response = CreateUserResponse(
            id=new_user_id,
            name=request_data.name,
            email=request_data.email,
            message="User created successfully"
        )
        
        return response.model_dump()
        
    except Exception as e:
        error_response = ErrorResponse(
            error="ValidationError",
            message=f"Invalid request data: {str(e)}"
        )
        return Response(
            status_code=400,
            content_type=content_types.APPLICATION_JSON,
            body=error_response.model_dump_json()
        )


@app.get("/csv-upload")
def csv_upload_page() -> Response:
    """CSV upload interface page"""
    template = jinja_env.get_template('csv_upload.html')
    html_content = template.render()
    
    return Response(
        status_code=200,
        content_type=content_types.TEXT_HTML,
        body=html_content
    )


@app.post("/csv-preview")
def csv_preview() -> Dict[str, Any]:
    """Handle CSV file upload and return preview data"""
    
    try:
        # Check if services are initialized
        if not s3_service or not dynamodb_service:
            error_response = ErrorResponse(
                error="ServiceUnavailable",
                message="AWS services not properly configured"
            )
            return Response(
                status_code=503,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
        
        # Get file from multipart form data
        content_type = app.current_event.headers.get("content-type", "")
        if not content_type.startswith("multipart/form-data"):
            error_response = ErrorResponse(
                error="InvalidContentType",
                message="Expected multipart/form-data"
            )
            return Response(
                status_code=400,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
        
        # Parse multipart data (simplified approach for Lambda)
        body = app.current_event.body
        if app.current_event.is_base64_encoded:
            body = base64.b64decode(body)
        
        # Extract file content and filename from multipart data
        file_content, filename = parse_multipart_file(body, content_type)
        
        if not file_content or not filename:
            error_response = ErrorResponse(
                error="NoFileProvided",
                message="No file provided in request"
            )
            return Response(
                status_code=400,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
        
        # Validate CSV file
        is_valid, error_msg = validate_csv_file(file_content, filename)
        if not is_valid:
            error_response = ErrorResponse(
                error="InvalidFile",
                message=error_msg
            )
            return Response(
                status_code=400,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
        
        # Parse CSV and return preview
        preview_response = parse_csv_content(file_content)
        return preview_response.model_dump()
        
    except Exception as e:
        error_response = ErrorResponse(
            error="ProcessingError",
            message=f"Failed to process CSV file: {str(e)}"
        )
        return Response(
            status_code=500,
            content_type=content_types.APPLICATION_JSON,
            body=error_response.model_dump_json()
        )


@app.post("/csv-submit")
def csv_submit() -> Dict[str, Any]:
    """Handle CSV file submission - save to S3 and write to DynamoDB"""
    
    try:
        # Check if services are initialized
        if not s3_service or not dynamodb_service:
            error_response = ErrorResponse(
                error="ServiceUnavailable",
                message="AWS services not properly configured"
            )
            return Response(
                status_code=503,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
        
        # Get file from multipart form data
        content_type = app.current_event.headers.get("content-type", "")
        if not content_type.startswith("multipart/form-data"):
            error_response = ErrorResponse(
                error="InvalidContentType",
                message="Expected multipart/form-data"
            )
            return Response(
                status_code=400,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
        
        # Parse multipart data
        body = app.current_event.body
        if app.current_event.is_base64_encoded:
            body = base64.b64decode(body)
        
        # Extract file content and filename from multipart data
        file_content, filename = parse_multipart_file(body, content_type)
        
        if not file_content or not filename:
            error_response = ErrorResponse(
                error="NoFileProvided",
                message="No file provided in request"
            )
            return Response(
                status_code=400,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
        
        # Validate CSV file
        is_valid, error_msg = validate_csv_file(file_content, filename)
        if not is_valid:
            error_response = ErrorResponse(
                error="InvalidFile",
                message=error_msg
            )
            return Response(
                status_code=400,
                content_type=content_types.APPLICATION_JSON,
                body=error_response.model_dump_json()
            )
        
        # Save raw CSV to S3
        s3_file_key = s3_service.upload_csv_file(file_content, filename)
        
        # Extract valid rows for DynamoDB
        valid_rows = extract_valid_rows(file_content)
        
        # Write to DynamoDB
        records_written = 0
        if valid_rows:
            records_written = dynamodb_service.write_csv_data(valid_rows, s3_file_key)
        
        # Return success response
        upload_response = CSVUploadResponse(
            status="success",
            message=f"Successfully processed {len(valid_rows)} rows",
            s3_file_key=s3_file_key,
            dynamodb_records_written=records_written
        )
        
        return upload_response.model_dump()
        
    except Exception as e:
        error_response = ErrorResponse(
            error="ProcessingError",
            message=f"Failed to process CSV file: {str(e)}"
        )
        return Response(
            status_code=500,
            content_type=content_types.APPLICATION_JSON,
            body=error_response.model_dump_json()
        )


def parse_multipart_file(body_bytes: bytes, content_type: str) -> Tuple[bytes, str]:
    """
    Parse multipart form data to extract file content and filename.
    Simplified implementation for CSV upload.
    """
    try:
        # Extract boundary from content-type header
        boundary = None
        if "boundary=" in content_type:
            boundary = content_type.split("boundary=")[1].split(";")[0]
        
        if not boundary:
            return None, None
        
        # Convert to string for parsing
        body_str = body_bytes.decode('utf-8', errors='ignore')
        
        # Split by boundary
        parts = body_str.split(f"--{boundary}")
        
        for part in parts:
            if 'filename=' in part and 'name="file"' in part:
                # Extract filename
                filename = None
                for line in part.split('\n'):
                    if 'filename=' in line:
                        # Handle both single and double quotes
                        if 'filename="' in line:
                            filename = line.split('filename="')[1].split('"')[0]
                        elif "filename='" in line:
                            filename = line.split("filename='")[1].split("'")[0]
                        break
                
                # Extract file content (after double CRLF or double LF)
                content_start = part.find('\r\n\r\n')
                if content_start == -1:
                    content_start = part.find('\n\n')
                
                if content_start != -1 and filename:
                    file_content = part[content_start + 4:].rstrip('\r\n-')
                    # Remove any trailing boundary markers
                    if file_content.endswith(f"--{boundary}"):
                        file_content = file_content[:-len(f"--{boundary}")]
                    return file_content.encode('utf-8'), filename
        
        return None, None
        
    except Exception as e:
        print(f"Error parsing multipart data: {e}")
        return None, None


@app.exception_handler(Exception)
def handle_exception(ex: Exception) -> Dict[str, Any]:
    """Global exception handler"""
    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred"
    )
    return error_response.model_dump()


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Main Lambda handler"""
    return app.resolve(event, context)