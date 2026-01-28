from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from dependencies import *
import worker.peak_value as peak_value
import logger
import time
import pandas as pd
import json
import numpy as np
from anyio import to_thread
import asyncio
import threading

router = APIRouter()
rtm_data = {}


def appendCSV(data: pd.DataFrame, path: str, name: str):
    """
    `data` is the DataFrame\n
    `path` is the directory\n
    `name` is the file name
    """
    p = os.path.join(path, name)
    if not os.path.exists(path):
        os.makedirs(path)
    if os.path.exists(p):
        df1 = pd.read_csv(p)
        if not df1.empty:
            data = pd.concat([df1, data], ignore_index=True)
        else:
            print(p, "empty")
    data.to_csv(p, index=False)


async def process(data: dict):              
    station_id = data["id"]
    # 1. Convert to NumPy Array (Fast)
    raw_data = np.array([[i["dt"], i["x"], i["y"], i["z"]]
                        for i in data["data"]])
    rtm_data[station_id] = peak_value.get_filtered_peak_value(raw_data[:, 1:4])
    relative_ms = raw_data[:, 0]

    # clock check and overflow adjustment
    diffs = np.diff(relative_ms, prepend=relative_ms[0])
    overflow_indices = np.where(diffs < -4000000)[0]  # big drop
    if len(overflow_indices) > 0:
        for idx in overflow_indices:
            relative_ms[idx:] += 4294967.296
    anchor = lastCountTime[station_id]
    timestamps = anchor + (relative_ms / 1000.0)
    if (time.time() - anchor) > 4294900 and relative_ms[0] < 2000:
        lastCountTime[station_id] += 4294967.296
        logger.warning(
            f"Overflow detected for {station_id}, adjusting anchor.")

    # 3. Determine "Hour Keys" for every sample
    # This creates an array of strings like "2026.1.19.19"
    hour_keys = np.array(
        [time.strftime("%Y.%m.%d.%H", time.gmtime(t)) for t in timestamps])

    # 4. Find unique hours in this batch
    unique_hours = np.unique(hour_keys)

    for hour in unique_hours:
        # Mask the data that belongs to this specific hour
        mask = (hour_keys == hour)
        hour_data = raw_data[mask]
        hour_timestamps = timestamps[mask]

        # Combine timestamps back with x, y, z
        # Result: [timestamp, x, y, z]
        final_table = np.column_stack((hour_timestamps, hour_data[:, 1:]))

        # Convert to DataFrame and append to CSV
        df = pd.DataFrame(final_table, columns=["time", "x", "y", "z"])

        await manager.broadcast({
            "dt": [time.strftime("%H:%M:%S", time.localtime(t)) for t in hour_timestamps],
            "x": (hour_data[:, 1] * dataRatio).tolist(),
            "y": (hour_data[:, 2] * dataRatio).tolist(),
            "z": (hour_data[:, 3] * dataRatio).tolist()
        })
        logger.success(f"successfully processed data from {data['id']}.")
        p = hour.split(".")
        path = os.path.join("data", station_id, *p[:-1])
        name = f"{p[-1]}.csv"
        await to_thread.run_sync(appendCSV, df, path, name)


@router.websocket("/ws/data/{client_id}")
async def websocket_data_endpoint(websocket: WebSocket, client_id: str, background: BackgroundTasks):
    await websocket.accept()
    logger.info(f"ESP32 {client_id} connected via WebSocket")

    if client_id not in lastCountTime:
        lastCountTime[client_id] = time.time()
        logger.info(f"{client_id} auto-registered via WS")

    try:
        while True:
            # 1. Receive JSON data from ESP32
            data_json = await websocket.receive_text()
            raw_payload = json.loads(data_json)
            msg_type = raw_payload.get("type", "")
            client_id = raw_payload.get("id", "")
            data = raw_payload.get("data", [])

            if msg_type == "warning":
                station_data = station_config[client_id]
                payload = {
                    "author": "TPSEM",
                    "type": "eew",
                    "data": {
                        "lat": station_data["lat"],
                        "lng": station_data["lng"],
                        "pga": data.get("pga", 0.0),
                        "pgv": data.get("pgv", 0.0),
                    }
                }
                mqtt_client.publish("tpsem/warning", json.dumps(payload))

            elif msg_type == "data":
                if client_id in lastCountTime:
                    logger.success(f"{client_id} is registered!")
                    asyncio.create_task(process(raw_payload))
                    logger.info(f"Data length: {len(raw_payload['data'])}.")
                else:
                    await websocket.send_text("restart")
                    continue

            elif msg_type == "init":
                logger.info(f"{client_id} is registering...")
                lastCountTime[client_id] = time.time() - data.get("time", 0)
                logger.success(f"{client_id} registered successfully.")

            await websocket.send_text("ack")

    except WebSocketDisconnect:
        logger.warning(f"ESP32 {client_id} disconnected")
    except Exception as e:
        logger.error(f"WS Error: {e}")

def rtm_loop():
    logger.info("RTM MQTT loop started.")
    while True:
        time.sleep(1)
        data = []
        for i in rtm_data:
            pga, pgv = rtm_data[i]
            station_data = station_config.get(i, {})
            data.append({
                "name": station_data.get("name", ""),
                "name_en": station_data.get("name_en", ""),
                "lat": station_data.get("lat", 0.0),
                "lng": station_data.get("lng", 0.0),
                "pga": pga,
                "pgv": pgv
            })
        payload = {
            "author": "TPSEM",
            "type": "rtm",
            "data": data
        }
        mqtt_client.publish("tpsem/rtm", json.dumps(payload))

threading.Thread(target=rtm_loop, daemon=True).start()