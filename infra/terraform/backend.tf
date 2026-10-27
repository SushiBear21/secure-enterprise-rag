terraform {
  backend "s3" {
    bucket = "secure-rag-tfstate-359769212511-96d6e247c37c1329e2b97a8742"
    key    = "secure-enterprise-rag/sandbox/terraform.tfstate"
    region = "us-east-1"

    profile             = "portfolio-sandbox"
    allowed_account_ids = ["359769212511"]

    encrypt      = true
    use_lockfile = true
  }
}