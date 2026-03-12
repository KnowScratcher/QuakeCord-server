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

router = APIRouter()
station_queues = defaultdict(asyncio.Queue)
worker_tasks = {}
rtm_data = {}
last_interest = {}
previous_data: dict[str, np.ndarray] = {}
warnings = {}
warnings_lock = False
warnings_update = False
messages = []
dmc = DiscordMessageControl(discord_channels)
warning_data = {
    "prev_pgs": (0.0, 0.0),
    "prev_result": [False] * 3,
    "warnings": warnings,
    "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
}
last_warning_time = 0
COOL_DOWN_TIME = 20

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


async def station_worker(station_id: str):
    """A persistent worker that processes data in order for a specific station."""
    while True:
        data = await station_queues[station_id].get()
        while not station_queues[station_id].empty():
            data["data"].extend(station_queues[station_id].get_nowait()["data"])
        try:
            # Your existing process logic here
            await process(data)
        except Exception as e:
            logger.error(f"Worker error for {station_id}: {e}")
        finally:
            station_queues[station_id].task_done()


async def clean_warning_data():
    for station in warnings:
        if time.time() - warnings[station]["timestamp"] > 30:
            warnings.pop(station, None)


async def alert_check(client_id: str, data: np.ndarray) -> None:  # data = 3d array
    global last_interest, warnings_lock, warnings_update, messages, warning_data, last_warning_time
    try:
        result, interest, prev_data = alert.run_alert_tests(client_id, data, last_interest.get(client_id, 0), previous_data.get(client_id)) # type: ignore
    except Exception as e:
        logger.error(f"Error in alert_check: {e}")
        result, interest, prev_data = [], 0, np.array([])
    last_interest[client_id] = interest
    previous_data[client_id] = prev_data
    if any(result):
        last_warning_time = time.time()
        logger.warning(
            f"Alert triggered! Interest: {interest}, Results: {result}")
        try:
            await clean_warning_data()
        except Exception as e:
            logger.error(f"Error in clean_warning_data: {e}")
        station_data = station_config[client_id]
        warnings[client_id] = {
            "lat": round(station_data.get("lat", 0.0), 2),  # for location security
            "lng": round(station_data.get("lng", 0.0), 2),
            "pga": rtm_data.get(client_id, (0.0, 0.0))[0],
            "pgv": rtm_data.get(client_id, (0.0, 0.0))[1],
            "timestamp": time.time()
        }
        payload = {
            "author": "TPSEM",
            "type": "warning",
            "data": list(warnings.values())
        }
        mqtt_client.publish("tpsem/warning", json.dumps(payload))

        if not warnings_lock:
            add_to_quake_buffer(client_id, get_buffer(client_id)[-500:] * ratio)
            warnings_lock = True
            await dmc.init()
            await dmc.add_warning(warnings, result)
        else:
            add_to_quake_buffer(client_id, data*ratio)
            if any(rtm_data.get(station, (0.0, 0.0))[0] - warning_data["prev_pgs"][0] > 5 or rtm_data.get(station, (0.0, 0.0))[1] - warning_data["prev_pgs"][1] > 5 for station in warnings):
                warnings_update = True
        if warnings_update:
            warnings_update = False
            await dmc.edit_warning_data(warnings, result)
    else:
        if (time.time() - last_warning_time) < 20:
            add_to_quake_buffer(client_id, data*ratio)
        else:
            if warnings_lock:
                warnings_lock = False
                await dmc.send_plot()
                report.generate_report(warning_data)
                warnings.clear()
                reset_quake_buffer()


async def process(data: dict):
    station_id = data["id"]
    raw_data = np.array([[i["dt"], i["x"], i["y"], i["z"]]
                        for i in data["data"]])
    try:
        rtm_data[station_id] = peak_value.get_filtered_peak_value(
            raw_data[:, 1:4])
    except Exception as e:
        logger.error(f"Error in get_filtered_peak_value: {e}")
        rtm_data[station_id] = (0.0, 0.0)
    await alert_check(station_id, raw_data[:, 1:4])
    relative_ms = raw_data[:, 0]

    # clock check and overflow adjustment
    diffs = np.diff(relative_ms, prepend=relative_ms[0])
    overflow_indices = np.where(diffs < -4000000)[0]  # big drop
    if len(overflow_indices) > 0:
        for idx in overflow_indices:
            relative_ms[idx:] += 4294967.296
    anchor = lastCountTime[station_id]
    timestamps = anchor + (relative_ms / 1000.0)
    logger.log(f"ESP timestamp: {relative_ms[-1]/1000}, last timestamp: {timestamps[-1]}, which in real time is {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamps[-1]))}, now is {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}, q size: {station_queues[station_id].qsize()}")
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

        # await manager.broadcast({
        #     "dt": [time.strftime("%H:%M:%S", time.localtime(t)) for t in hour_timestamps],
        #     "x": (hour_data[:, 1] * dataRatio).tolist(),
        #     "y": (hour_data[:, 2] * dataRatio).tolist(),
        #     "z": (hour_data[:, 3] * dataRatio).tolist()
        # })
        logger.success(f"successfully processed data from {data['id']}, hour {hour}.")
        p = hour.split(".")
        path = os.path.join("data", station_id, *p[:-1])
        name = f"{p[-1]}.csv"
        await to_thread.run_sync(appendCSV, df, path, name)
    print("done")


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
                                station_worker(client_id))
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


def rtm_loop():
    logger.info("RTM MQTT loop started.")
    mqtt_client = get_mqtt_client()
    while True:
        time.sleep(2)
        data = []
        for i in rtm_data:
            pga, pgv = rtm_data[i]
            station_data = station_config.get(i, {})
            data.append({
                "name": station_data.get("name", ""),
                "name_en": station_data.get("name_en", ""),
                "lat": round(station_data.get("lat", 0.0), 2),
                # for location security
                "lng": round(station_data.get("lng", 0.0), 2),
                "pga": pga,
                "pgv": pgv
            })
        payload = {
            "author": "TPSEM",
            "type": "rtm",
            "data": data
        }
        res = mqtt_client.publish("tpsem/rtm", json.dumps(payload))
        print(res)


threading.Thread(target=rtm_loop, daemon=True).start()
