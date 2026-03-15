#!/bin/bash
# Wait for OpenSearch to be active, then set up the index and update .env
set -e

ENV_FILE="$(dirname "$0")/../.env"
REGION="ap-south-1"
DOMAIN="legal-rag-search"
SETUP_SCRIPT="$(dirname "$0")/setup/create_index.py"

echo "⏳ Waiting for OpenSearch domain '$DOMAIN' to become active..."

while true; do
    ENDPOINT=$(aws opensearch describe-domain --domain-name "$DOMAIN" --region "$REGION" \
        --query "DomainStatus.Endpoint" --output text 2>/dev/null)
    PROCESSING=$(aws opensearch describe-domain --domain-name "$DOMAIN" --region "$REGION" \
        --query "DomainStatus.Processing" --output text 2>/dev/null)
    
    if [[ "$ENDPOINT" != "None" && "$ENDPOINT" != "" && "$PROCESSING" == "False" ]]; then
        echo "✅ OpenSearch is ACTIVE! Endpoint: $ENDPOINT"
        break
    fi
    
    echo "   Still processing... (checking again in 30s)"
    sleep 30
done

# Update .env with the endpoint
sed -i '' "s|OPENSEARCH_ENDPOINT=.*|OPENSEARCH_ENDPOINT=https://$ENDPOINT|" "$ENV_FILE"
echo "✅ Updated .env: OPENSEARCH_ENDPOINT=https://$ENDPOINT"

# Create the index
echo "📦 Creating OpenSearch index..."
cd "$(dirname "$0")/../backend"
python3 ../scripts/setup/create_index.py

echo ""
echo "🎉 OpenSearch setup complete!"
echo "   Endpoint: https://$ENDPOINT"
echo "   Run 'bash scripts/test_pipelines.sh' to test both pipelines"
