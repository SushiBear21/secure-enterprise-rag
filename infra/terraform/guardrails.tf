resource "aws_bedrock_guardrail" "assistant" {
  name        = "secure-rag-guardrail"
  description = "Detect prompt attacks in synthetic RAG requests and evidence"

  blocked_input_messaging   = "This request was blocked by the security filter."
  blocked_outputs_messaging = "This response was blocked by the security filter."

  content_policy_config {
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }
}

resource "aws_bedrock_guardrail_version" "assistant" {
  guardrail_arn = aws_bedrock_guardrail.assistant.guardrail_arn
  description   = "Initial prompt attack protection"

  lifecycle {
    replace_triggered_by = [aws_bedrock_guardrail.assistant]
  }
}

output "guardrail_id" {
  value = aws_bedrock_guardrail.assistant.guardrail_id
}

output "guardrail_version" {
  value = aws_bedrock_guardrail_version.assistant.version
}