import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from dependencies import *
import worker.peak_value as peak_value
import worker.alert as alert
import worker.report as report
import logger
import time
import pandas as pd
import json
import numpy as np
from anyio import to_thread
import asyncio
import threading
import hmac
import hashlib
import secrets
import numpy as np
from collections import defaultdict
import worker.filter as filter
import worker.process as process
import worker.rtm as rtm

router = APIRouter()
worker_tasks = {}

rtm.start()

@router.websocket("/ws/data/{client_id}")
async def websocket_data_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    logger.info(f"ESP32 {client_id} connected via WebSocket")
    nonce = secrets.token_hex(128)
    payload = {
        "type": "challenge",
        "data": nonce
    }
    await websocket.send_json(payload)
    try:
        data = await websocket.receive_json()
        if data.get("type", "") != "auth_response":
            await websocket.close(code=4003, reason="forbidden")
            return  # Forbidden
        client_data = data.get("data", {})
        client_hash = client_data.get("hash", "")
        secret = STATION_SECRETS.get(client_id, None)
        if not secret:
            await websocket.close(code=4003, reason="forbidden")
            return  # Forbidden

        expected_hash = hmac.new(
            secret.encode(), nonce.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(client_hash, expected_hash):
            await websocket.close(code=4003, reason="forbidden")
            return  # Forbidden
        await websocket.send_text("Authenticated")
        lastCountTime[client_id] = time.time() - (client_data.get("time", 0) / 1000.0)
        logger.success(f"ESP32 {client_id} authenticated successfully.")
        logger.log(f"ESP32 time is {client_data.get('time', 0)}, lastCountTime set to {lastCountTime[client_id]}")
        while True:
            try:
                # 1. Receive JSON data from ESP32
                data_json = await websocket.receive_text()
                raw_payload = json.loads(data_json)
                msg_type = raw_payload.get("type", "")
                client_id = raw_payload.get("id", "")
                data = raw_payload.get("data", [])

                if msg_type == "data":
                    if client_id in lastCountTime:
                        logger.success(f"{client_id} is registered!")
                        await station_queues[client_id].put(raw_payload)
                        if client_id not in worker_tasks or worker_tasks[client_id].done():
                            worker_tasks[client_id] = asyncio.create_task(
                                process.station_worker(client_id))
                        logger.info(
                            f"Data length: {len(raw_payload['data'])}.")
                    else:
                        await websocket.send_text("restart")
                        continue

                elif msg_type == "init":
                    logger.info(f"{client_id} is registering...")
                    lastCountTime[client_id] = time.time() - \
                        data.get("time", 0)
                    logger.success(f"{client_id} registered successfully.")

                await websocket.send_text("ack")
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON received. Error: " + str(e))
                await websocket.send_text("error: invalid json")

    except WebSocketDisconnect:
        logger.warning(f"ESP32 {client_id} disconnected")
    except Exception as e:
        logger.error(f"WS Error: {e}")
