from aws_cdk import(
    Stack,
    CfnOutput,
    aws_lambda,
    aws_apigateway as apigateway,
    aws_wafv2 as wafv2,
)

from cdk_aws_lambda_powertools_layer import LambdaPowertoolsLayer
from constructs import Construct

class AwsPowertoolsLambdaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ##################
        ## Lambda Stuff ##
        ##################

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
            code=aws_lambda.Code.from_asset('./apigateway_v1/lambda'),
            description='Lambda function with Powertools.',
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            handler='api_gateway_lambda.lambda_handler',
            layers=[powertoolsLayer],
        )

        ##########################
        ## API Gateway v1 Stuff ##
        ##########################
        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigateway.LambdaRestApi.html
        rest_api = apigateway.LambdaRestApi(
            self,
            'RestAPI',
            description='Rest API with Lambda integration.',
            handler=lambda_func,
        )

        ###############
        ## WAF Stuff ##
        ###############
        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.html
        cfn_web_acl = wafv2.CfnWebACL(
            self,
            "WAFv2",
            description="WAFv2 for Rest API",
            scope="REGIONAL", # Only other option is CLOUDFRONT, and that must be deployed to us-east-1.
            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.DefaultActionProperty.html#count
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            rules=[
                # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.RuleProperty.html
                wafv2.CfnWebACL.RuleProperty(
                    name="IpRateLimiter",
                    priority=1,
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.StatementProperty.html
                    statement=wafv2.CfnWebACL.StatementProperty(
                        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.RateBasedStatementProperty.html
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            aggregate_key_type="IP",
                            # Per 5 minute period:
                            limit=10, # TODO: CHANGE ME!! (Just this low to validate it works...)
                        )
                    ),
                    # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.VisibilityConfigProperty.html
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="IpRateLimiter",
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.VisibilityConfigProperty.html
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="WAFv2",
                sampled_requests_enabled=True,
            ),
        )

        ### Tie the WAFv2 to the HttpApi:
        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACLAssociation.html
        wafv2.CfnWebACLAssociation(self, 'ApiGatewayWafAssociation', resource_arn=rest_api.deployment_stage.stage_arn, web_acl_arn=cfn_web_acl.attr_arn)

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.CfnOutput.html
        CfnOutput(
            self,
            "ApiUrl",
            value=rest_api.url,
            description="The url for our API Gateway v2.",
        )
