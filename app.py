#!/usr/bin/env python3
import os

import aws_cdk as cdk

from aws_powertools_lambda.aws_powertools_lambda_stack import AwsPowertoolsLambdaStack

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
