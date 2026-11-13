from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import ConnectionManager
from sqlalchemy import select
from app.db.database import SessionLocal
from app.utils.auth import verify_token, is_token_valid
from app.models.user import User

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/ws/messages")
async def websocket_messages(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    payload = verify_token(token)
    if not payload:
        await websocket.close(code=1008)
        return

    # Verify token exists in DB (catches revoked/logged-out tokens), then look up the user.
    # The session is released before the long-lived socket loop starts.
    async with SessionLocal() as db:
        if not await is_token_valid(token, db):
            await websocket.close(code=1008)
            return

        user = (await db.execute(select(User).where(User.username == payload.get("username")))).scalar_one_or_none()
        if not user:
            await websocket.close(code=1008)
            return
        user_id = str(user.id)

    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(user_id, websocket)
