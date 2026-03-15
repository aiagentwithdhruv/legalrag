#!/bin/bash
# Step 3: Create IAM roles for Lambda and ECS
set -e

echo "--- [3/5] Creating IAM roles ---"

LAMBDA_ROLE_NAME="legalrag-lambda-role"
ECS_TASK_ROLE_NAME="legalrag-ecs-task-role"
ECS_EXEC_ROLE_NAME="legalrag-ecs-execution-role"

# ── Lambda Role ──────────────────────────────────────────────

if aws iam get-role --role-name "$LAMBDA_ROLE_NAME" 2>/dev/null; then
  echo "  Lambda role already exists"
else
  aws iam create-role \
    --role-name "$LAMBDA_ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }'
  echo "  Created Lambda role: $LAMBDA_ROLE_NAME"
fi

# Lambda inline policy
aws iam put-role-policy \
  --role-name "$LAMBDA_ROLE_NAME" \
  --policy-name "legalrag-lambda-policy" \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
      {
        \"Effect\": \"Allow\",
        \"Action\": [
          \"bedrock:InvokeModel\",
          \"bedrock:InvokeModelWithResponseStream\"
        ],
        \"Resource\": [
          \"arn:aws:bedrock:$AWS_REGION::foundation-model/amazon.titan-embed-text-v2:0\",
          \"arn:aws:bedrock:$AWS_REGION::foundation-model/amazon.titan-text-premier-v1:0\",
          \"arn:aws:bedrock:$AWS_REGION::foundation-model/anthropic.claude-sonnet-4-6\",
          \"arn:aws:bedrock:$AWS_REGION::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0\"
        ]
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"s3:GetObject\", \"s3:PutObject\", \"s3:HeadObject\"],
        \"Resource\": \"arn:aws:s3:::$S3_BUCKET_NAME/*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": \"s3:ListBucket\",
        \"Resource\": \"arn:aws:s3:::$S3_BUCKET_NAME\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"textract:DetectDocumentText\", \"textract:AnalyzeDocument\", \"textract:StartDocumentAnalysis\", \"textract:GetDocumentAnalysis\"],
        \"Resource\": \"*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"comprehend:DetectEntities\", \"comprehend:DetectKeyPhrases\"],
        \"Resource\": \"*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"dynamodb:PutItem\", \"dynamodb:GetItem\", \"dynamodb:UpdateItem\", \"dynamodb:DeleteItem\", \"dynamodb:Query\"],
        \"Resource\": [
          \"arn:aws:dynamodb:$AWS_REGION:$AWS_ACCOUNT_ID:table/$DEDUP_TABLE\",
          \"arn:aws:dynamodb:$AWS_REGION:$AWS_ACCOUNT_ID:table/$SESSIONS_TABLE\"
        ]
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"es:ESHttpGet\", \"es:ESHttpPost\", \"es:ESHttpPut\", \"es:ESHttpDelete\", \"es:ESHttpHead\"],
        \"Resource\": \"arn:aws:es:$AWS_REGION:$AWS_ACCOUNT_ID:domain/$OPENSEARCH_DOMAIN_NAME/*\"
      },
      {
        \"Effect\": \"Allow\",
        \"Action\": [\"logs:CreateLogGroup\", \"logs:CreateLogStream\", \"logs:PutLogEvents\"],
        \"Resource\": \"arn:aws:logs:$AWS_REGION:$AWS_ACCOUNT_ID:*\"
      }
    ]
  }"
echo "  Lambda policy attached"

# Attach basic Lambda execution
aws iam attach-role-policy \
  --role-name "$LAMBDA_ROLE_NAME" \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>/dev/null || true

echo "✓ IAM roles ready: $LAMBDA_ROLE_NAME"
