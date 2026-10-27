resource "aws_lambda_function" "api" {
  function_name = "secure-rag-api"
  role          = aws_iam_role.api.arn
  runtime       = "python3.13"
  handler       = "api_handler.lambda_handler"

  filename         = "${path.module}/../../.build/api.zip"
  source_code_hash = filebase64sha256("${path.module}/../../.build/api.zip")

  memory_size = 256
  timeout     = 30

  depends_on = [
    aws_iam_role_policy.api_logs,
    aws_cloudwatch_log_group.api
  ]
}

resource "aws_apigatewayv2_api" "assistant" {
  name          = "secure-rag-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_authorizer" "assistant" {
  api_id           = aws_apigatewayv2_api.assistant.id
  name             = "cognito"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.assistant.id]
    issuer   = "https://cognito-idp.us-east-1.amazonaws.com/${aws_cognito_user_pool.assistant.id}"
  }
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.assistant.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "whoami" {
  api_id    = aws_apigatewayv2_api.assistant.id
  route_key = "GET /whoami"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"

  authorization_type   = "JWT"
  authorizer_id        = aws_apigatewayv2_authorizer.assistant.id
  authorization_scopes = ["secure-rag/ask"]
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.assistant.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 5
    throttling_rate_limit  = 2
  }
}

resource "aws_lambda_permission" "whoami" {
  statement_id  = "AllowWhoamiFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"

  source_account = "359769212511"
  source_arn     = "${aws_apigatewayv2_api.assistant.execution_arn}/*/GET/whoami"
}

output "api_base_url" {
  value = aws_apigatewayv2_api.assistant.api_endpoint
}
resource "aws_apigatewayv2_route" "ask" {
  api_id    = aws_apigatewayv2_api.assistant.id
  route_key = "POST /ask"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"

  authorization_type   = "JWT"
  authorizer_id        = aws_apigatewayv2_authorizer.assistant.id
  authorization_scopes = ["secure-rag/ask"]
}

resource "aws_lambda_permission" "ask" {
  statement_id  = "AllowAskFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"

  source_account = "359769212511"
  source_arn     = "${aws_apigatewayv2_api.assistant.execution_arn}/*/POST/ask"
}