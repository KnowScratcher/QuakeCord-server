import os
import logger
from fastapi.websockets import WebSocket
from worker import history
import paho.mqtt.client as mqtt
import json

basePath = os.path.dirname(__file__)
""" The base dir """
dataPath = os.path.join(basePath, "data")
""" The data directory """
dataRatio = 980.0 / 8028.6
""" The experiment data for data -> gal """

lastCountTime: dict[str, float] = {}
""" Record of the last count time of each station, this value will change about every 49 days """

class ConnectionManager:
    """ Websocket control"""
    def __init__(self):
        self.activate:list[WebSocket] = []
    async def connect(self, ws:WebSocket):
        await ws.accept()
        self.activate.append(ws)
        logger.info("client connected")
        await ws.send_json(history.getHistory(dataRatio))
    async def disconnect(self, ws):
        self.activate.remove(ws)
        logger.info("client disconnected")

    async def broadcast(self, msg:dict):
        for connection in self.activate:
            try:
                await connection.send_json(msg)
            except:
                self.activate.remove(connection)

manager = ConnectionManager()
""" Websocket manager"""

mqtt_client = mqtt.Client()
""" MQTT client """ 
with open(os.path.join(basePath, "config.json"), "r", encoding="utf-8") as f:
    mqtt_config = json.load(f)
mqtt_client.username_pw_set(mqtt_config.get("username", ""), mqtt_config.get("password", ""))
mqtt_client.connect(mqtt_config.get("host", "localhost"), mqtt_config.get("port", 1883), mqtt_config.get("keepalive", 60))

global station_config
with open(os.path.join(basePath, "station.json"), "r", encoding="utf-8") as f:
    station_config = json.load(f)