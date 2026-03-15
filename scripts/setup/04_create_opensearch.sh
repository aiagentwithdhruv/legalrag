#!/bin/bash
# Step 4: Create OpenSearch Managed Domain
set -e

echo "--- [4/5] Creating OpenSearch domain: $OPENSEARCH_DOMAIN_NAME ---"

if aws opensearch describe-domain --domain-name "$OPENSEARCH_DOMAIN_NAME" --region "$AWS_REGION" 2>/dev/null; then
  echo "  OpenSearch domain already exists."
  OPENSEARCH_ENDPOINT=$(aws opensearch describe-domain \
    --domain-name "$OPENSEARCH_DOMAIN_NAME" \
    --region "$AWS_REGION" \
    --query "DomainStatus.Endpoint" --output text)
  echo "  Endpoint: https://$OPENSEARCH_ENDPOINT"
else
  echo "  Creating domain (takes 10-15 minutes)..."

  aws opensearch create-domain \
    --domain-name "$OPENSEARCH_DOMAIN_NAME" \
    --region "$AWS_REGION" \
    --engine-version "OpenSearch_2.17" \
    --cluster-config "InstanceType=$OPENSEARCH_INSTANCE_TYPE,InstanceCount=$OPENSEARCH_INSTANCE_COUNT" \
    --ebs-options "EBSEnabled=true,VolumeType=gp3,VolumeSize=$OPENSEARCH_EBS_SIZE" \
    --node-to-node-encryption-options "Enabled=true" \
    --encryption-at-rest-options "Enabled=true" \
    --domain-endpoint-options "EnforceHTTPS=true" \
    --advanced-security-options "{
      \"Enabled\": true,
      \"InternalUserDatabaseEnabled\": true,
      \"MasterUserOptions\": {
        \"MasterUserName\": \"$OPENSEARCH_MASTER_USER\",
        \"MasterUserPassword\": \"$OPENSEARCH_MASTER_PASSWORD\"
      }
    }" \
    --access-policies "{
      \"Version\": \"2012-10-17\",
      \"Statement\": [{
        \"Effect\": \"Allow\",
        \"Principal\": {\"AWS\": \"arn:aws:iam::$AWS_ACCOUNT_ID:role/legalrag-lambda-role\"},
        \"Action\": \"es:*\",
        \"Resource\": \"arn:aws:es:$AWS_REGION:$AWS_ACCOUNT_ID:domain/$OPENSEARCH_DOMAIN_NAME/*\"
      }, {
        \"Effect\": \"Allow\",
        \"Principal\": {\"AWS\": \"arn:aws:iam::$AWS_ACCOUNT_ID:user/Aiwithdhruv_Claude\"},
        \"Action\": \"es:*\",
        \"Resource\": \"arn:aws:es:$AWS_REGION:$AWS_ACCOUNT_ID:domain/$OPENSEARCH_DOMAIN_NAME/*\"
      }]
    }"

  echo "  Domain creation started. Waiting for ACTIVE status (~10-15 min)..."
  aws opensearch wait domain-active --domain-name "$OPENSEARCH_DOMAIN_NAME" --region "$AWS_REGION" 2>/dev/null || \
    echo "  (wait command not available, check console)"

  OPENSEARCH_ENDPOINT=$(aws opensearch describe-domain \
    --domain-name "$OPENSEARCH_DOMAIN_NAME" \
    --region "$AWS_REGION" \
    --query "DomainStatus.Endpoint" --output text)

  echo "  Endpoint: https://$OPENSEARCH_ENDPOINT"
  echo ""
  echo "  → Update .env:"
  echo "    OPENSEARCH_ENDPOINT=https://$OPENSEARCH_ENDPOINT"
fi

echo "✓ OpenSearch domain ready: $OPENSEARCH_DOMAIN_NAME"
