from aws_cdk import(
    Stack,
    CfnOutput,
    aws_lambda,
    aws_apigateway as apigateway,
    aws_wafv2 as wafv2,
)

from constructs import Construct

# TODO: CHANGE ME!! (Just this low to validate it works...)
REQUEST_LIMIT_PER_MIN = 10

class AwsPowertoolsLambdaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ##################
        ## Lambda Stuff ##
        ##################
        lambda_runtime = aws_lambda.Runtime.PYTHON_3_12
        ## Get the powertools arn from:
        # https://docs.powertools.aws.dev/lambda/python/latest/
        ## Import it with CDK:
        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_lambda.LayerVersion.html#static-fromwbrlayerwbrversionwbrarnscope-id-layerversionarn
        python_version = lambda_runtime.name.lower().replace('.', '') # pylint: disable=no-member (it's complaining about 'name' for some reason)
        powertools_layer = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            'LambdaPowertoolsLayer',
            f'arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-{python_version}-x86_64:4',
        )

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_lambda.Function.html
        lambda_func = aws_lambda.Function(
            self,
            'LambdaFunction',
            code=aws_lambda.Code.from_asset('./apigateway_v1/lambda'),
            description='Lambda function with Powertools.',
            runtime=lambda_runtime,
            handler='api_gateway_lambda.lambda_handler',
            layers=[powertools_layer],
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
        # NOTE: If this is ever moved behind CloudFront or any loadbalancer/proxy, you'll need to
        # use the IP address in the header instead (x-forwarded-for). Users can change this though,
        # so you don't want to trust the one *they* provide, create it yourself. If you DON'T do this,
        # you'll only see the CloudFront / Proxy's IP address at the WAF.

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.StatementProperty.html
        rate_limit_statement = wafv2.CfnWebACL.StatementProperty(
            rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                aggregate_key_type="CUSTOM_KEYS",
                # Default is 5 minutes, but 1 min is easier to think about:
                evaluation_window_sec=60,
                limit=REQUEST_LIMIT_PER_MIN,
                # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.RateBasedStatementCustomKeyProperty.html
                custom_keys=[
                    wafv2.CfnWebACL.RateBasedStatementCustomKeyProperty(
                        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.RateLimitUriPathProperty.html
                        uri_path=wafv2.CfnWebACL.RateLimitUriPathProperty(
                            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.TextTransformationProperty.html
                            text_transformations=[wafv2.CfnWebACL.TextTransformationProperty(
                                priority=0,
                                # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-wafv2-webacl-texttransformation.html#cfn-wafv2-webacl-texttransformation-type
                                type="NONE",
                            )]
                        ),
                    ),
                    # This IP block must not be the first element in this list. That's how
                    # aws knows for sure you're not ONLY declaring the IP block.
                    # (If that's what you want, there's another `aggregate_key_type` for that).
                    wafv2.CfnWebACL.RateBasedStatementCustomKeyProperty(
                        ip={},
                    ),
                ],
            )
        )

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.html
        cfn_web_acl = wafv2.CfnWebACL(
            self,
            "WAFv2",
            description=f"WAFv2 for {rest_api.rest_api_name} - {rest_api.rest_api_id}",
            scope="REGIONAL", # Only other option is CLOUDFRONT, and that must be deployed to us-east-1.
            # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.DefaultActionProperty.html#count
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            rules=[
                # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.RuleProperty.html
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimiter",
                    priority=1,
                    action=wafv2.CfnWebACL.RuleActionProperty(
                        block=wafv2.CfnWebACL.BlockActionProperty(
                            custom_response=wafv2.CfnWebACL.CustomResponseProperty(response_code=429),
                        ),
                    ),
                    statement=rate_limit_statement,
                    # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_wafv2.CfnWebACL.VisibilityConfigProperty.html
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimiter",
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
            description="The url for our API Gateway",
        )
