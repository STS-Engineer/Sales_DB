import json
from fastapi import APIRouter, Request, Header, HTTPException
from app.settings import settings
from app.services.monday import MondayClient, verify_signature_or_skip, ITEM_QUERY
from app.services.ingest import build_row, insert_row

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/monday")
async def monday_webhook(request: Request, x_monday_signature: str | None = Header(default=None)):
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        payload = {}

    # Webhook creation handshake
    if isinstance(payload, dict) and payload.get("challenge"):
        return {"challenge": payload["challenge"]}

    # Optional verification (skipped if secret is empty)
    if not verify_signature_or_skip(raw, x_monday_signature, settings.MONDAY_SIGNING_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = payload.get("event") or {}
    if str(event.get("boardId")) != str(settings.BOARD_ID):
        return {"ok": True, "skipped": "wrong_board"}

    changed_col = str(event.get("columnId"))
    if settings.TRIGGER_COLUMN_IDS and changed_col not in settings.TRIGGER_COLUMN_IDS:
        return {"ok": True, "skipped": "not_tracked"}

    item_id = event.get("itemId") or event.get("pulseId")
    if not item_id:
        return {"ok": True, "skipped": "no_item_id"}

    client = MondayClient(settings.MONDAY_API_TOKEN)
    data = await client.graphql(ITEM_QUERY, {"item_id": int(item_id)})
    items = data.get("items") or []
    if not items:
        return {"ok": True, "skipped": "item_not_found"}

    row = build_row(items[0])
    insert_row(row)
    return {"ok": True, "inserted": True, "item_id": items[0].get("id")}
