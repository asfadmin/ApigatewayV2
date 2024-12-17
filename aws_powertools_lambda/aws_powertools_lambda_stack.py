from aws_cdk import(
    Stack,
    CfnOutput,
    aws_lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_wafv2 as wafv2,
)

from cdk_aws_lambda_powertools_layer import LambdaPowertoolsLayer
from constructs import Construct


class AwsPowertoolsLambdaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # https://github.com/aws-powertools/powertools-lambda-layer-cdk
        powertoolsLayer = LambdaPowertoolsLayer(
            self,
            'PowertoolsLayer',
            include_extras=True,
            runtime_family=aws_lambda.RuntimeFamily.PYTHON,
        )

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_lambda.Function.html
        lambda_func = aws_lambda.Function(
            self,
            'LambdaFunction',
            code=aws_lambda.Code.from_asset('./aws_powertools_lambda/lambda'),
            description='Lambda function with Powertools.',
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler='api_gateway_lambda.lambda_handler',
            layers=[powertoolsLayer],
        )
        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2_integrations.HttpLambdaIntegration.html
        lambda_integration = apigwv2_integrations.HttpLambdaIntegration("LambdaIntegration", lambda_func)

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.HttpApi.html
        http_api = apigwv2.HttpApi(
            self,
            "HttpApiPowertools",
            description="HttpApi with Powertools",  
        )

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.AddRoutesOptions.html#path
        http_api.add_routes(
            path="/",
            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.HttpMethod.html
            methods=[apigwv2.HttpMethod.ANY],
            integration=lambda_integration,
        )
        http_api.add_routes(
            path="/{proxy+}",
            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.HttpMethod.html
            methods=[apigwv2.HttpMethod.ANY],
            integration=lambda_integration,
        )

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.CfnOutput.html
        CfnOutput(
            self,
            "ApiUrl",
            value=http_api.url,
            description="The url for our API Gateway v2.",
        )
