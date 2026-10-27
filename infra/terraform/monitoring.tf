resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/secure-rag-api"
  retention_in_days = 14
}
resource "aws_sns_topic" "operations" {
  name = "secure-rag-operations"
}

output "operations_topic_arn" {
  value = aws_sns_topic.operations.arn
}
resource "aws_cloudwatch_metric_alarm" "api_server_errors" {
  alarm_name        = "secure-rag-api-server-errors"
  alarm_description = "At least one API server error in five minutes"

  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.assistant.id
  }

  alarm_actions = [aws_sns_topic.operations.arn]
  ok_actions    = [aws_sns_topic.operations.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name        = "secure-rag-lambda-errors"
  alarm_description = "At least one Lambda execution error in five minutes"

  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_actions = [aws_sns_topic.operations.arn]
  ok_actions    = [aws_sns_topic.operations.arn]
}
resource "aws_cloudwatch_metric_alarm" "api_latency" {
  alarm_name        = "secure-rag-api-high-latency"
  alarm_description = "Average API latency exceeds 10 seconds for two consecutive five-minute periods"

  namespace           = "AWS/ApiGateway"
  metric_name         = "Latency"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 10000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.assistant.id
  }

  alarm_actions = [aws_sns_topic.operations.arn]
  ok_actions    = [aws_sns_topic.operations.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name        = "secure-rag-lambda-throttles"
  alarm_description = "At least one Lambda invocation throttled in five minutes"

  namespace           = "AWS/Lambda"
  metric_name         = "Throttles"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api.function_name
  }

  alarm_actions = [aws_sns_topic.operations.arn]
  ok_actions    = [aws_sns_topic.operations.arn]
}