import logger
import time
import json
import threading
from dependencies import mqtt_client, rtm_data, station_config

def rtm_loop():
    logger.info("RTM MQTT loop started.")
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

def start():
    threading.Thread(target=rtm_loop, daemon=True).start()