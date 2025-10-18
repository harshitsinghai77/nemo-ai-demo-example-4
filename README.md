# AWS Lambda API with Powertools

A serverless API built with AWS Lambda, Powertools, and Function URLs.

## Features

- AWS Lambda with Function URLs
- AWS Powertools for Python
- Pydantic for data validation
- AWS CDK for infrastructure
- GitHub Actions for CI/CD

## API Endpoints

- `GET /ping` - Health check endpoint
- `GET /hello` - Hello world endpoint

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Deploy infrastructure:
```bash
cd infrastructure
cdk deploy
```

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black .
```