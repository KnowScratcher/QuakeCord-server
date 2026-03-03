from fastapi import WebSocket
from fastapi.routing import APIRouter
import logger
from dependencies import *
from worker import history


router = APIRouter()

@router.websocket("/ws/monitoring")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
                await websocket.receive_text()
    except:
        await manager.disconnect(websocket)