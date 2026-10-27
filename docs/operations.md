# Operations guide

## Environment

- AWS account: Portfolio-Sandbox, 359769212511
- Region: us-east-1
- CLI profile: portfolio-sandbox
- Application Terraform: infra/terraform
- State-storage Terraform: infra/bootstrap

## Authentication

Refresh administrator CLI access:

    aws sso login --profile portfolio-sandbox

Application users authenticate through Cognito with MFA.
The backend derives document audiences from verified groups.

## Logs

Application log group:

    /aws/lambda/secure-rag-api

API access log group:

    /aws/apigateway/secure-rag-api

Application records include request IDs, route, HTTP status,
outcome, and duration. They omit tokens, questions, answers,
and document contents.

Match api_request_id in application logs to request_id in
API access logs. Requests rejected before Lambda invocation
appear only in API access logs.

Read recent application logs:

    aws logs tail /aws/lambda/secure-rag-api --since 10m --region us-east-1 --profile portfolio-sandbox

Read recent API access logs:

    aws logs tail /aws/apigateway/secure-rag-api --since 10m --region us-east-1 --profile portfolio-sandbox

Both log groups retain logs for 14 days.

## Alarms

All alarms notify the secure-rag-operations SNS topic.

- API server errors: at least one 5xx in five minutes.
- Lambda errors: at least one execution error in five minutes.
- API latency: average above 10 seconds for two consecutive
  five-minute periods.
- Lambda throttling: at least one throttle in five minutes.

Missing data is treated as not breaching.

The email subscription was created outside Terraform and
confirmed manually. Recreating the topic requires subscribing
and confirming the email again.

Alarm-to-email delivery was verified using a temporary alarm
state change. A real failure crossing the metric threshold has
not yet been tested.

Lambda throttling alarms do not cover API Gateway rate-limit
rejections. API-wide average latency can hide individual slow
requests.

## Troubleshooting

- 401: check login, token expiry, issuer, and client.
- 403: check required scope and recognized Cognito groups.
- 400: send only a question containing 1–1000 characters.
- blocked: guardrail intervention; inspect the synthetic test
  case without adding sensitive content to logs.
- insufficient_evidence: accessible evidence could not answer.
- 5xx: correlate request IDs, inspect Lambda runtime logs,
  IAM permissions, Bedrock availability, and timeouts.

Handled application errors may not increment Lambda Errors.
The API 5xx alarm covers their HTTP failure responses.

## Deployment

From the repository root, rebuild all four runtime modules:

    Compress-Archive -Path .\app\monitored_handler.py, .\app\api_handler.py, .\app\authorization.py, .\app\rag_service.py -DestinationPath .\.build\api.zip -Force

Then:

    Set-Location .\infra\terraform
    terraform fmt
    terraform validate
    terraform plan -out="deploy.tfplan"

Review the plan before applying:

    terraform apply "deploy.tfplan"

Run the relevant application and security checks after changes.

## Terraform state

Application state uses this S3 bucket:

    secure-rag-tfstate-359769212511-96d6e247c37c1329e2b97a8742

Object key:

    secure-enterprise-rag/sandbox/terraform.tfstate

Controls:
- S3-managed AES256 encryption
- Versioning
- Public access blocked
- Bucket-owner-enforced ownership
- HTTPS-only bucket policy
- Native S3 state locking

Migration preserved all 43 application resources.
The post-migration plan reported no changes.
The remote state object's encryption and version ID were verified.

Bootstrap manages six state-storage resources separately.
Its state remains local in infra/bootstrap and was copied to
a timestamped folder under $HOME\TerraformBackups.
Application state was also backed up there before migration.

Keep those backups protected. Never commit state or saved plans.
Do not force-unlock state without checking for another active run.
State-version recovery has not yet been rehearsed.

## Network design

The API is publicly reachable and uses Cognito JWT authorization.
Lambda is not attached to a customer VPC.
This is not a private-endpoint deployment.

Document and state buckets have public access blocked.
The application role has scoped Bedrock permissions.
Administrator development tools remain privileged and can bypass
the application's user-facing authorization path.

## Cost review

On 2026-10-27, displayed month-to-date cost was $0.02.
The $10 monthly budget was confirmed present.
Billing data can lag usage; a budget alert is not a spending cap.

Monitor model and guardrail requests, storage, KMS, CloudWatch
logs and alarms, and other service charges.

## Cleanup

Closing the terminal does not delete AWS resources.

Before teardown:
1. Back up state and confirm which data must be retained.
2. Review a destroy plan from infra/terraform.
3. Account for versioned S3 objects and vector data that may
   prevent deletion.
4. Keep the state bucket available throughout application cleanup.

Bootstrap is separate and its bucket has prevent_destroy enabled.
Do not remove state storage as part of routine application cleanup.