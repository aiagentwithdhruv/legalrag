#!/bin/bash
# Step 1: Create S3 bucket for legal documents
set -e

echo "--- [1/5] Creating S3 bucket: $S3_BUCKET_NAME ---"

# Create bucket
if aws s3 ls "s3://$S3_BUCKET_NAME" 2>/dev/null; then
  echo "  Bucket already exists, skipping."
else
  aws s3api create-bucket \
    --bucket "$S3_BUCKET_NAME" \
    --region "$AWS_REGION" \
    --create-bucket-configuration LocationConstraint="$AWS_REGION" 2>/dev/null || \
  aws s3api create-bucket \
    --bucket "$S3_BUCKET_NAME" \
    --region "$AWS_REGION"
  echo "  Created bucket: $S3_BUCKET_NAME"
fi

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket "$S3_BUCKET_NAME" \
  --versioning-configuration Status=Enabled
echo "  Versioning enabled"

# Block public access
aws s3api put-public-access-block \
  --bucket "$S3_BUCKET_NAME" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
echo "  Public access blocked"

# Enable server-side encryption (AES-256, free)
aws s3api put-bucket-encryption \
  --bucket "$S3_BUCKET_NAME" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
      "BucketKeyEnabled": true
    }]
  }'
echo "  Server-side encryption enabled (AES-256)"

# CORS for frontend uploads
aws s3api put-bucket-cors \
  --bucket "$S3_BUCKET_NAME" \
  --cors-configuration '{
    "CORSRules": [{
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }]
  }'
echo "  CORS configured"

echo "✓ S3 bucket ready: s3://$S3_BUCKET_NAME"
