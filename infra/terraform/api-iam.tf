resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/secure-rag-api"
  retention_in_days = 14
}

resource "aws_iam_role" "api" {
  name = "secure-rag-api"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "api_logs" {
  name = "write-api-logs"
  role = aws_iam_role.api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "WriteApiLogs"
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "${aws_cloudwatch_log_group.api.arn}:*"
    }]
  })
}
resource "aws_iam_role_policy" "api_bedrock" {
  name = "query-rag-knowledge-base"
  role = aws_iam_role.api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "RetrieveDocumentEvidence"
        Effect   = "Allow"
        Action   = "bedrock:Retrieve"
        Resource = aws_bedrockagent_knowledge_base.documents.arn
      },
      {
        Sid      = "GenerateAnswer"
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0"
      }
    ]
  })
}
