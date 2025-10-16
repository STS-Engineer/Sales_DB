import hmac, hashlib
from typing import Optional, Any, Dict
import httpx

MONDAY_GRAPHQL_URL = "https://api.monday.com/v2"

ITEM_QUERY = """
query GetItem($item_id: [ID!]!) {
  items (ids: $item_id) {
    id
    name
    board { id }
    column_values { id text value }
  }
}
"""

class MondayClient:
    def __init__(self, api_token: str):
        self.headers = {"Authorization": api_token, "Content-Type": "application/json"}

    async def graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                MONDAY_GRAPHQL_URL,
                headers=self.headers,
                json={"query": query, "variables": variables or {}},
            )
            res.raise_for_status()
            data = res.json()
            if "errors" in data:
                raise RuntimeError(str(data["errors"]))
            return data["data"]

def verify_signature_or_skip(raw_body: bytes, signature: Optional[str], signing_secret: Optional[str]) -> bool:
    # If no secret is configured, skip verification (return True)
    if not signing_secret:
        return True
    if not signature:
        return False
    digest = hmac.new(signing_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
