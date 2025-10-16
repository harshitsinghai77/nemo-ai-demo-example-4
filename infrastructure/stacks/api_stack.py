from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
)
from constructs import Construct


class ApiStack(Stack):
    """
    CDK Stack for the Nemo AI Demo API with CSV upload functionality.
    
    This stack provisions:
    - Lambda function with Function URL
    - S3 bucket for CSV file storage
    - DynamoDB table for user data storage
    - Required IAM permissions
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize the API stack.
        
        Args:
            scope: The scope in which to define this construct
            construct_id: The scoped construct ID
            **kwargs: Additional keyword arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for CSV storage
        csv_bucket = s3.Bucket(
            self,
            "CsvStorageBucket",
            bucket_name="nemo-ai-demo-example-4-bucket",  # As specified in Jira story
            public_read_access=False,
            public_write_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,  # For demo purposes
        )

        # DynamoDB Table for user data
        user_data_table = dynamodb.Table(
            self,
            "UserDataTable",
            table_name="nemo-ai-demo-example-4-user-data",
            partition_key=dynamodb.Attribute(
                name="entry_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For demo purposes
        )

        # Lambda execution role
        lambda_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Grant Lambda permissions to S3 and DynamoDB
        csv_bucket.grant_read_write(lambda_role)
        user_data_table.grant_read_write_data(lambda_role)

        # Lambda function
        api_function = _lambda.Function(
            self,
            "ApiFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../lambda-deployment.zip"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "POWERTOOLS_SERVICE_NAME": "api-service",
                "POWERTOOLS_METRICS_NAMESPACE": "ApiService",
                "LOG_LEVEL": "INFO",
                "S3_BUCKET_NAME": csv_bucket.bucket_name,
                "DYNAMODB_TABLE_NAME": user_data_table.table_name,
            },
        )

        # Function URL
        function_url = api_function.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
            cors=_lambda.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[
                    _lambda.HttpMethod.GET, 
                    _lambda.HttpMethod.POST,
                    _lambda.HttpMethod.PUT,
                    _lambda.HttpMethod.DELETE
                ],
                allowed_headers=["*"],
                allow_credentials=False,
                max_age=Duration.seconds(300),
            ),
        )

        # Outputs
        CfnOutput(
            self,
            "FunctionUrl",
            value=function_url.url,
            description="Lambda Function URL",
        )

        CfnOutput(
            self,
            "FunctionName",
            value=api_function.function_name,
            description="Lambda Function Name",
        )

        CfnOutput(
            self,
            "S3BucketName",
            value=csv_bucket.bucket_name,
            description="S3 Bucket for CSV Storage",
        )

        CfnOutput(
            self,
            "DynamoDBTableName",
            value=user_data_table.table_name,
            description="DynamoDB Table for User Data",
        )