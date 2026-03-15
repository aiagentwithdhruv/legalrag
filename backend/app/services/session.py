"""Session history management via DynamoDB."""
import time
from app.utils.aws_clients import get_dynamodb
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
MAX_HISTORY = 10  # keep last 10 messages per session


def get_history(session_id: str) -> list[dict]:
    """Load last N messages for a session."""
    s = get_settings()
    table = get_dynamodb().Table(s.sessions_table)
    try:
        response = table.query(
            KeyConditionExpression="session_id = :sid",
            ExpressionAttributeValues={":sid": session_id},
            ScanIndexForward=False,
            Limit=MAX_HISTORY,
        )
        items = sorted(response.get("Items", []), key=lambda x: x["timestamp"])
        return [{"role": item["role"], "content": item["content"]} for item in items]
    except Exception as e:
        logger.warning(f"Failed to load session {session_id}: {e}")
        return []


def save_message(session_id: str, role: str, content: str, sources: list = None) -> None:
    s = get_settings()
    table = get_dynamodb().Table(s.sessions_table)
    ttl = int(time.time()) + 86400  # 24h TTL
    item = {
        "session_id": session_id,
        "timestamp": str(time.time()),
        "role": role,
        "content": content,
        "expires_at": ttl,
    }
    if sources:
        item["sources"] = sources
    try:
        table.put_item(Item=item)
    except Exception as e:
        logger.warning(f"Failed to save session message: {e}")
