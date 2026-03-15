"""Cached boto3 client factory — one client per service per process."""
import boto3
from functools import lru_cache
from app.config import get_settings


@lru_cache
def get_s3():
    s = get_settings()
    return boto3.client("s3", region_name=s.aws_region)


@lru_cache
def get_bedrock():
    s = get_settings()
    return boto3.client("bedrock-runtime", region_name=s.aws_region)


@lru_cache
def get_textract():
    s = get_settings()
    return boto3.client("textract", region_name=s.aws_region)


@lru_cache
def get_comprehend():
    s = get_settings()
    return boto3.client("comprehend", region_name=s.aws_region)


@lru_cache
def get_dynamodb():
    s = get_settings()
    return boto3.resource("dynamodb", region_name=s.aws_region)


def get_opensearch_client():
    """OpenSearch client with HTTP basic auth (managed domain)."""
    from opensearchpy import OpenSearch, RequestsHttpConnection
    s = get_settings()
    host = s.opensearch_endpoint.replace("https://", "").replace("http://", "")
    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=(s.opensearch_master_user, s.opensearch_master_password),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
    )
