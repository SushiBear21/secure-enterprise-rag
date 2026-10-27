resource "aws_iam_role" "bedrock_kb" {
  name = "secure-rag-bedrock-kb"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "bedrock.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = "359769212511"
        }
        ArnLike = {
          "aws:SourceArn" = "arn:aws:bedrock:us-east-1:359769212511:knowledge-base/CIDAASDHVV"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_kb" {
  name = "secure-rag-kb-permissions"
  role = aws_iam_role.bedrock_kb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListSourceBucket"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.documents.arn
        Condition = {
          StringEquals = {
            "aws:ResourceAccount" = "359769212511"
          }
        }
      },
      {
        Sid      = "ReadDocumentPrefix"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.documents.arn}/documents/*"
      },
      {
        Sid      = "InvokeEmbeddingModel"
        Effect   = "Allow"
        Action   = "bedrock:InvokeModel"
        Resource = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
      },
      {
        Sid    = "UseDocumentVectorIndex"
        Effect = "Allow"
        Action = [
          "s3vectors:GetIndex",
          "s3vectors:GetVectors",
          "s3vectors:QueryVectors",
          "s3vectors:PutVectors",
          "s3vectors:DeleteVectors"
        ]
        Resource = aws_s3vectors_index.documents.index_arn
      },
      {
        Sid      = "DecryptSourceDocuments"
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = aws_kms_key.documents.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.us-east-1.amazonaws.com"
          }
        }
      },
      {
        Sid    = "UseEncryptedVectorStorage"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.documents.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3vectors.us-east-1.amazonaws.com"
          }
        }
      },
      {
        Sid      = "DescribeStorageKey"
        Effect   = "Allow"
        Action   = "kms:DescribeKey"
        Resource = aws_kms_key.documents.arn
      }
    ]
  })
}

output "bedrock_kb_role_arn" {
  value = aws_iam_role.bedrock_kb.arn
}