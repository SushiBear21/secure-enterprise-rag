terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region              = "us-east-1"
  profile             = "portfolio-sandbox"
  allowed_account_ids = ["359769212511"]

  default_tags {
    tags = {
      Project     = "SecureEnterpriseRAG"
      Environment = "Sandbox"
      ManagedBy   = "Terraform"
      DataClass   = "Synthetic"
    }
  }
}

resource "aws_kms_key" "documents" {
  description             = "Encrypt synthetic RAG documents"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "EnableAccountIAMPermissions"
      Effect = "Allow"
      Principal = {
        AWS = "arn:aws:iam::359769212511:root"
      }
      Action   = "kms:*"
      Resource = "*"
    }]
  })
}

resource "aws_kms_alias" "documents" {
  name          = "alias/secure-rag-documents"
  target_key_id = aws_kms_key.documents.key_id
}

resource "aws_s3_bucket" "documents" {
  bucket_prefix = "secure-rag-documents-"
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.documents.arn
    }

    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource = [
        aws_s3_bucket.documents.arn,
        "${aws_s3_bucket.documents.arn}/*"
      ]
      Condition = {
        Bool = {
          "aws:SecureTransport"       = "false"
          "aws:PrincipalIsAWSService" = "false"
        }
      }
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.documents]
}

output "document_bucket_name" {
  value = aws_s3_bucket.documents.id
}

output "document_kms_key_arn" {
  value = aws_kms_key.documents.arn
}