resource "aws_bedrockagent_knowledge_base" "documents" {
  name        = "secure-enterprise-rag"
  description = "Synthetic enterprise documents for secure RAG testing"
  role_arn    = aws_iam_role.bedrock_kb.arn

  knowledge_base_configuration {
    type = "VECTOR"

    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"

      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = 1024
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }

  storage_configuration {
    type = "S3_VECTORS"

    s3_vectors_configuration {
      index_arn = aws_s3vectors_index.documents.index_arn
    }
  }

  depends_on = [aws_iam_role_policy.bedrock_kb]
}

resource "aws_bedrockagent_data_source" "documents" {
  name                 = "synthetic-enterprise-documents"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.documents.id
  data_deletion_policy = "DELETE"

  data_source_configuration {
    type = "S3"

    s3_configuration {
      bucket_arn         = aws_s3_bucket.documents.arn
      inclusion_prefixes = ["documents/synthetic/"]
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"

      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }
}

output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.documents.id
}

output "knowledge_base_arn" {
  value = aws_bedrockagent_knowledge_base.documents.arn
}

output "data_source_id" {
  value = aws_bedrockagent_data_source.documents.data_source_id
}