resource "aws_cognito_resource_server" "assistant" {
  identifier   = "secure-rag"
  name         = "Secure RAG API"
  user_pool_id = aws_cognito_user_pool.assistant.id

  scope {
    scope_name        = "ask"
    scope_description = "Submit questions to the RAG API"
  }
}

resource "aws_cognito_user_pool_client" "assistant" {
  name         = "secure-rag-local-client"
  user_pool_id = aws_cognito_user_pool.assistant.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  supported_identity_providers         = ["COGNITO"]

  allowed_oauth_scopes = [
    "openid",
    "${aws_cognito_resource_server.assistant.identifier}/ask"
  ]

  callback_urls = ["http://localhost:8000/callback"]
  logout_urls   = ["http://localhost:8000/"]

  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true
  explicit_auth_flows           = ["ALLOW_REFRESH_TOKEN_AUTH"]

  access_token_validity  = 15
  id_token_validity      = 15
  refresh_token_validity = 1

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_pool_domain" "assistant" {
  domain                = "secure-rag-359769212511"
  user_pool_id          = aws_cognito_user_pool.assistant.id
  managed_login_version = 1
}

output "auth_client_id" {
  value = aws_cognito_user_pool_client.assistant.id
}

output "auth_base_url" {
  value = "https://${aws_cognito_user_pool_domain.assistant.domain}.auth.us-east-1.amazoncognito.com"
}