import json
import pytest
from moto import mock_lambda
from src.handler import lambda_handler


def test_index_endpoint():
    """Test the index endpoint returns HTML"""
    event = {
        "requestContext": {"http": {"method": "GET", "path": "/"}},
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {"accept": "text/html"},
        "queryStringParameters": None,
        "body": None,
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    assert "text/html" in response["headers"]["content-type"]
    assert "AWS Lambda API Service" in response["body"]


def test_ping_endpoint():
    """Test the ping endpoint"""
    event = {
        "requestContext": {"http": {"method": "GET", "path": "/ping"}},
        "rawPath": "/ping",
        "rawQueryString": "",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "pong"
    assert body["status"] == "healthy"


def test_hello_endpoint_without_name():
    """Test the hello endpoint without name parameter"""
    event = {
        "requestContext": {"http": {"method": "GET", "path": "/hello"}},
        "rawPath": "/hello",
        "rawQueryString": "",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Hello, World!"
    assert body["name"] is None


def test_hello_endpoint_with_name():
    """Test the hello endpoint with name parameter"""
    event = {
        "requestContext": {"http": {"method": "GET", "path": "/hello"}},
        "rawPath": "/hello",
        "rawQueryString": "name=John",
        "headers": {},
        "queryStringParameters": {"name": "John"},
        "body": None,
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Hello, John!"
    assert body["name"] == "John"


def test_status_endpoint():
    """Test the status endpoint"""
    event = {
        "requestContext": {"http": {"method": "GET", "path": "/status"}},
        "rawPath": "/status",
        "rawQueryString": "",
        "headers": {},
        "queryStringParameters": None,
        "body": None,
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "healthy"
    assert "timestamp" in body
    assert body["version"] == "1.0.0"


def test_get_user_json():
    """Test getting user with JSON response"""
    event = {
        "requestContext": {"http": {"method": "GET", "path": "/users/1"}},
        "rawPath": "/users/1",
        "pathParameters": {"user_id": "1"},
        "rawQueryString": "",
        "headers": {"accept": "application/json"},
        "queryStringParameters": None,
        "body": None,
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["id"] == "1"
    assert body["name"] == "John Doe"
    assert body["email"] == "john@example.com"


def test_get_user_html():
    """Test getting user with HTML response"""
    event = {
        "requestContext": {"http": {"method": "GET", "path": "/users/1"}},
        "rawPath": "/users/1",
        "pathParameters": {"user_id": "1"},
        "rawQueryString": "",
        "headers": {"accept": "text/html"},
        "queryStringParameters": None,
        "body": None,
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    assert "text/html" in response["headers"]["content-type"]
    assert "John Doe" in response["body"]


def test_get_user_not_found():
    """Test getting non-existent user"""
    event = {
        "requestContext": {"http": {"method": "GET", "path": "/users/999"}},
        "rawPath": "/users/999",
        "pathParameters": {"user_id": "999"},
        "rawQueryString": "",
        "headers": {"accept": "application/json"},
        "queryStringParameters": None,
        "body": None,
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 404


def test_create_user():
    """Test creating a new user"""
    event = {
        "requestContext": {"http": {"method": "POST", "path": "/users"}},
        "rawPath": "/users",
        "rawQueryString": "",
        "headers": {"content-type": "application/json"},
        "queryStringParameters": None,
        "body": json.dumps({"name": "Test User", "email": "test@example.com"}),
    }
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["name"] == "Test User"
    assert body["email"] == "test@example.com"
    assert body["message"] == "User created successfully"