resource "aws_cognito_user_pool" "assistant" {
  name = "secure-rag-users"

  username_configuration {
    case_sensitive = false
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 14
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 1
  }

  mfa_configuration = "ON"

  software_token_mfa_configuration {
    enabled = true
  }
}

resource "aws_cognito_user_group" "employees" {
  name         = "employees"
  user_pool_id = aws_cognito_user_pool.assistant.id
  description  = "Access to general employee documents"
}

resource "aws_cognito_user_group" "soc_analysts" {
  name         = "soc_analysts"
  user_pool_id = aws_cognito_user_pool.assistant.id
  description  = "Access to general employee and SOC documents"
}

resource "aws_cognito_user_group" "acquisition_team" {
  name         = "acquisition_team"
  user_pool_id = aws_cognito_user_pool.assistant.id
  description  = "Access to general employee and acquisition documents"
}

output "user_pool_id" {
  value = aws_cognito_user_pool.assistant.id
}

output "user_pool_arn" {
  value = aws_cognito_user_pool.assistant.arn
}