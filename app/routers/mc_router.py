from app.utils.decorators import event_handler
from fastapi import APIRouter, Request
from app.utils.logger import logger
import json

router = APIRouter()

@router.post("/mc_webhook")
async def handle_event(request: Request):

    payload = await request.json()
    event = payload.get("event")
    data = payload.get("data", {})
    print(payload)

    try:
        await event_handler.call_event(payload)
    except Exception as e:
        logger.error(f"Error handling event at /mc_webhook: {event}: {e}")

    return {"status": "ok"}
