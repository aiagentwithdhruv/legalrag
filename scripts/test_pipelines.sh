#!/bin/bash
# Quick pipeline test script — run after enabling Bedrock model access
set -e

cd "$(dirname "$0")/../backend"

echo "======================================="
echo "  LegalRAG Pipeline Tests"
echo "======================================="

# Test 1: Bedrock Embedding
echo ""
echo "--- Test 1: Bedrock Titan V2 Embedding ---"
python3 -c "
import boto3, json
b = boto3.client('bedrock-runtime', region_name='ap-south-1')
resp = b.invoke_model(
    modelId='amazon.titan-embed-text-v2:0',
    body=json.dumps({'inputText': 'arbitration clause', 'dimensions': 1024, 'normalize': True}),
    contentType='application/json', accept='application/json'
)
result = json.loads(resp['body'].read())
print(f'  ✅ Embedding dims: {len(result[\"embedding\"])} (expected: 1024)')
print(f'  Sample values: {result[\"embedding\"][:3]}')
"

# Test 2: Nova Lite LLM
echo ""
echo "--- Test 2: Nova Lite LLM (Fast model) ---"
python3 -c "
import boto3, json
b = boto3.client('bedrock-runtime', region_name='ap-south-1')
resp = b.invoke_model_with_response_stream(
    modelId='apac.amazon.nova-lite-v1:0',
    body=json.dumps({
        'inferenceConfig': {'maxNewTokens': 50, 'temperature': 0.1},
        'messages': [{'role': 'user', 'content': [{'text': 'What is arbitration in Indian law? One sentence.'}]}]
    }),
)
result = ''
for event in resp['body']:
    d = json.loads(event['chunk']['bytes'])
    if 'contentBlockDelta' in d:
        result += d['contentBlockDelta'].get('delta', {}).get('text', '')
print(f'  ✅ Nova Lite response: {result[:100]}...')
"

# Test 3: Health check
echo ""
echo "--- Test 3: FastAPI Health ---"
curl -s http://localhost:8000/health | python3 -m json.tool

# Test 4: Full Pipeline 1 (ingest Case 1)
echo ""
echo "--- Test 4: Upload Case 1 to S3 ---"
python3 -c "
import boto3, sys
s3 = boto3.client('s3', region_name='ap-south-1')
with open('../sample-docs/indian_civil_case_1.txt', 'rb') as f:
    s3.put_object(Bucket='legal-rag-documents-615815645247', Key='documents/indian_civil_case_1.txt', Body=f.read())
print('  ✅ Case 1 uploaded to S3')
"

echo ""
echo "--- Test 5: Run ingestion via API ---"
curl -s -X POST http://localhost:8000/ingest/process \
  -H 'Content-Type: application/json' \
  -d '{
    "s3_key": "documents/indian_civil_case_1.txt",
    "filename": "indian_civil_case_1.txt",
    "doc_type": "case_law",
    "department": "legal",
    "clearance_level": "internal"
  }' | python3 -m json.tool

echo ""
echo "--- Test 6: Query Pipeline ---"
curl -s -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What was the Supreme Court ruling on the arbitration clause in the insurance case?",
    "session_id": "test-session-001",
    "use_smart_model": false
  }' | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
        data="${line#data: }"
        if [[ "$data" != "[DONE]" ]]; then
            echo "$data" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('content',''), end='', flush=True) if d.get('type')=='text' else None" 2>/dev/null
        fi
    fi
  done
echo ""
echo ""
echo "======================================="
echo "  All tests complete!"
echo "======================================="
