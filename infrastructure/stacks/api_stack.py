from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_lambda as _lambda,
    aws_iam as iam,
)
from constructs import Construct


class ApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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

        # Lambda function
        api_function = _lambda.Function(
            self,
            "ApiFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("../src"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "POWERTOOLS_SERVICE_NAME": "api-service",
                "POWERTOOLS_METRICS_NAMESPACE": "ApiService",
                "LOG_LEVEL": "INFO",
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