# Example Repo

Played around with getting apigatewayv2 hooked up to lambda, that uses powertools.

## ApiGatewayV2 vs ApiGatewayV1

(v2 is HttpAPI, v1 is RestAPI).

Originally we tried to get v2 to work. The problem is AWS currently doesn't support hooking up WAF to v2. If you want to rate-limit based on IP's, the only three options I see are:

- Don't, and hope the cost savings from v2 counter not having a WAF
- Do generic throttling that doesn't look at IP's. (You have `burst_limit` and `rate_limit` available [here](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_apigatewayv2.ThrottleSettings.html))
- Hook up a [Custom Lambda Authorizer](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-use-lambda-authorizer.html), and hook it up to a DB that records IP's short term. With the cost of the second lambda call plus the DB, your original lambda will have to be EXPENSIVE for this to save you money.
