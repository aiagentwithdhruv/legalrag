"""Create Pinecone serverless index for LegalRAG."""
import os
from pinecone import Pinecone, ServerlessSpec

def main():
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        print("Error: PINECONE_API_KEY not set")
        return

    index_name = os.environ.get("PINECONE_INDEX_NAME", "legalrag")
    dimensions = int(os.environ.get("EMBED_DIMENSIONS", "1536"))

    pc = Pinecone(api_key=api_key)

    existing = [idx.name for idx in pc.list_indexes()]
    if index_name in existing:
        print(f"Index '{index_name}' already exists — skipping creation")
        return

    print(f"Creating Pinecone index '{index_name}' ({dimensions} dims, cosine)...")
    pc.create_index(
        name=index_name,
        dimension=dimensions,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    print(f"Index '{index_name}' created successfully!")

if __name__ == "__main__":
    main()
