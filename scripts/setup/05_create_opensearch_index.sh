#!/bin/bash
# Step 5: Create OpenSearch index with knn_vector + BM25 mapping
set -e

echo "--- [5/5] Creating OpenSearch index: $OPENSEARCH_INDEX ---"

if [ -z "$OPENSEARCH_ENDPOINT" ]; then
  echo "ERROR: OPENSEARCH_ENDPOINT not set in .env"
  exit 1
fi

python3 scripts/setup/create_index.py
echo "✓ OpenSearch index ready: $OPENSEARCH_INDEX"
