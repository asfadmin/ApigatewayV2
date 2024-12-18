#!/usr/bin/env python3
import os

import aws_cdk as cdk


### API GATEWAY V2 ###
# from apigateway_v2.aws_powertools_lambda_stack import AwsPowertoolsLambdaStack

### API GATEWAY V1 ###
from apigateway_v1.aws_powertools_lambda_stack import AwsPowertoolsLambdaStack



app = cdk.App()
AwsPowertoolsLambdaStack(
    app,
    "AwsPowertoolsLambdaStack",
    description="Testing out ApiGateway + Lambda + Powertools",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION'),
    ),
)

app.synth()
