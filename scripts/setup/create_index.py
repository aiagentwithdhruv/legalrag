"""Create OpenSearch index with knn_vector + BM25 mapping."""
import os, sys, json
from dotenv import load_dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

load_dotenv()

ENDPOINT = os.environ["OPENSEARCH_ENDPOINT"].replace("https://", "")
INDEX    = os.environ.get("OPENSEARCH_INDEX", "legal-docs")
REGION   = os.environ.get("AWS_REGION", "us-east-1")
USER     = os.environ.get("OPENSEARCH_MASTER_USER", "admin")
PASS     = os.environ.get("OPENSEARCH_MASTER_PASSWORD", "")

# Use HTTP basic auth (managed OpenSearch with internal user database)
client = OpenSearch(
    hosts=[{"host": ENDPOINT, "port": 443}],
    http_auth=(USER, PASS),
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    pool_maxsize=20,
)

INDEX_BODY = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 512,
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
    "mappings": {
        "properties": {
            "chunk_id":        {"type": "keyword"},
            "doc_id":          {"type": "keyword"},
            "parent_chunk_id": {"type": "keyword"},
            "is_parent":       {"type": "boolean"},
            # BM25 full-text search
            "text": {
                "type": "text",
                "analyzer": "standard",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
            },
            # kNN vector
            "embedding": {
                "type": "knn_vector",
                "dimension": 1536,
                "method": {
                    "name": "hnsw",
                    "space_type": "innerproduct",
                    "engine": "faiss",
                    "parameters": {"ef_construction": 512, "m": 16},
                },
            },
            # Metadata for filtering + citations
            "metadata": {
                "properties": {
                    "source":          {"type": "keyword"},
                    "s3_key":          {"type": "keyword"},
                    "doc_type":        {"type": "keyword"},
                    "department":      {"type": "keyword"},
                    "clearance_level": {"type": "keyword"},
                    "page_number":     {"type": "integer"},
                    "section_heading": {"type": "keyword"},
                    "entities":        {"type": "keyword"},
                    "citation_id":     {"type": "keyword"},
                    "created_at":      {"type": "date"},
                    "file_hash":       {"type": "keyword"},
                }
            },
        }
    },
}

def main():
    if client.indices.exists(index=INDEX):
        print(f"  Index '{INDEX}' already exists.")
        mapping = client.indices.get_mapping(index=INDEX)
        dims = mapping[INDEX]["mappings"]["properties"]["embedding"]["dimension"]
        print(f"  Dimension: {dims}")
    else:
        response = client.indices.create(index=INDEX, body=INDEX_BODY)
        print(f"  Created index: {INDEX}")
        print(f"  Response: {json.dumps(response, indent=2)}")
    print(f"✓ OpenSearch index '{INDEX}' ready.")

if __name__ == "__main__":
    main()
