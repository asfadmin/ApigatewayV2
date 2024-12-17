from aws_cdk import(
    Stack,
    CfnOutput,
    aws_lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
)

from cdk_aws_lambda_powertools_layer import LambdaPowertoolsLayer
from constructs import Construct

# TODO:
#  - Test if we add the default_integration to the api directly, do we need the two routes?
#  - Test if we can remove the requirements.txt from the lambda function. If it needs it to pull from the layer or not.

# Throttling: Idk how to do it with IP. WAF doesn't support apigwv2, just v1. There's generic throttling in the gateway itself.
# The only other option I see rn is to use a custom lambda, https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html
# That'd mean hooking it up to a DB, to see previous requests. That's a lot for simple functionality, so I'm coming back to this.

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
            # We need to add the stage ourselves, so it has throttling:
            create_default_stage=False,
            # default_integration=lambda_integration,
        )
        # Method: https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.HttpApi.html#addwbrstageid-options
        # Returns: https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.HttpStage.html
        http_api_stage = http_api.add_stage(
            "HttpApiPowertoolsStage",
            # stage_name="$default", # Default name
            auto_deploy=True,
            description="Stage with Throttling for the HttpApi",
            throttle=apigwv2.ThrottleSettings(
                burst_limit=5,
                rate_limit=5,
            ),
        )

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.AddRoutesOptions.html#path
        http_api.add_routes(
            path="/",
            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.HttpMethod.html
            # methods=[apigwv2.HttpMethod.ANY], # Default
            integration=lambda_integration,
        )
        http_api.add_routes(
            path="/{proxy+}",
            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.HttpMethod.html
            # methods=[apigwv2.HttpMethod.ANY], # Default
            integration=lambda_integration,
        )

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.CfnOutput.html
        CfnOutput(
            self,
            "ApiUrl",
            value=http_api_stage.url,
            description="The url for our API Gateway v2.",
        )
