#!/bin/bash
# LegalRAG — Full AWS Setup (Automated)
# Run: bash scripts/setup/setup_all.sh
# Requires: AWS CLI configured with IAM user Aiwithdhruv_Claude

set -e

# ── Load .env ──────────────────────────────────────────────────
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
  exit 1
fi

echo "═══════════════════════════════════════════════"
echo "  LegalRAG AWS Setup"
echo "  Account: $(aws sts get-caller-identity --query Account --output text)"
echo "  Region:  $AWS_REGION"
echo "═══════════════════════════════════════════════"

bash scripts/setup/01_create_s3.sh
bash scripts/setup/02_create_dynamodb.sh
bash scripts/setup/03_create_iam_roles.sh
bash scripts/setup/04_create_opensearch.sh
bash scripts/setup/05_create_opensearch_index.sh
echo ""
echo "✓ All AWS resources created."
echo "→ Next: Enable Bedrock model access in AWS Console (one-time, manual)."
echo "  Models needed:"
echo "    - amazon.titan-embed-text-v2:0"
echo "    - amazon.titan-text-premier-v1:0"
echo "    - anthropic.claude-sonnet-4-6"
echo "  Console: https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess"
