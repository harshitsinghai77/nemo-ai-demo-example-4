import json
from typing import Dict, Any
from datetime import datetime, timedelta
from aws_lambda_powertools.event_handler import LambdaFunctionUrlResolver, Response, content_types
from aws_lambda_powertools.utilities.typing import LambdaContext
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from .models import (
    PingResponse, HelloResponse, StatusResponse, User, 
    CreateUserRequest, CreateUserResponse, ErrorResponse
)

app = LambdaFunctionUrlResolver()

# Initialize Jinja2 environment
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(['html', 'xml'])
)

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