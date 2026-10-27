resource "aws_s3vectors_vector_bucket" "documents" {
  vector_bucket_name = "secure-rag-vectors-359769212511"
  force_destroy      = false

  encryption_configuration {
    sse_type    = "aws:kms"
    kms_key_arn = aws_kms_key.documents.arn
  }
}

resource "aws_s3vectors_index" "documents" {
  index_name         = "enterprise-documents"
  vector_bucket_name = aws_s3vectors_vector_bucket.documents.vector_bucket_name

  data_type       = "float32"
  dimension       = 1024
  distance_metric = "cosine"

  encryption_configuration {
    sse_type    = "aws:kms"
    kms_key_arn = aws_kms_key.documents.arn
  }

  metadata_configuration {
    non_filterable_metadata_keys = [
      "AMAZON_BEDROCK_TEXT",
      "AMAZON_BEDROCK_METADATA"
    ]
  }
}

output "vector_bucket_name" {
  value = aws_s3vectors_vector_bucket.documents.vector_bucket_name
}

output "vector_index_arn" {
  value = aws_s3vectors_index.documents.index_arn
}