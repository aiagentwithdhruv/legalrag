#!/bin/bash
# Step 2: Create DynamoDB tables
set -e

echo "--- [2/5] Creating DynamoDB tables ---"

create_table_if_not_exists() {
  local TABLE_NAME=$1
  local KEY_SCHEMA=$2
  local ATTR_DEFS=$3

  if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" 2>/dev/null; then
    echo "  Table $TABLE_NAME already exists, skipping."
  else
    aws dynamodb create-table \
      --table-name "$TABLE_NAME" \
      --attribute-definitions "$ATTR_DEFS" \
      --key-schema "$KEY_SCHEMA" \
      --billing-mode PAY_PER_REQUEST \
      --region "$AWS_REGION"
    echo "  Created table: $TABLE_NAME"
    aws dynamodb wait table-exists --table-name "$TABLE_NAME" --region "$AWS_REGION"
    echo "  Table active: $TABLE_NAME"
  fi
}

# 1. Dedup table — file-level SHA-256 hash check
create_table_if_not_exists \
  "$DEDUP_TABLE" \
  "AttributeName=file_hash,KeyType=HASH" \
  "AttributeName=file_hash,AttributeType=S"

# Enable TTL on dedup table (1 year auto-expiry)
aws dynamodb update-time-to-live \
  --table-name "$DEDUP_TABLE" \
  --time-to-live-specification "Enabled=true,AttributeName=expires_at" \
  --region "$AWS_REGION" 2>/dev/null || true

# 2. Sessions table — conversation history
create_table_if_not_exists \
  "$SESSIONS_TABLE" \
  "AttributeName=session_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE" \
  "AttributeName=session_id,AttributeType=S AttributeName=timestamp,AttributeType=S"

# Enable TTL on sessions table (24h auto-expiry)
aws dynamodb update-time-to-live \
  --table-name "$SESSIONS_TABLE" \
  --time-to-live-specification "Enabled=true,AttributeName=expires_at" \
  --region "$AWS_REGION" 2>/dev/null || true

echo "✓ DynamoDB tables ready: $DEDUP_TABLE, $SESSIONS_TABLE"
