import os
import json
import logger
from worker import history
from fastapi import WebSocket
from .config import basePath, dataRatio
import paho.mqtt.client as mqtt
import paho.mqtt.enums as mqttApi

class ConnectionManager:
    """ Websocket control"""

    def __init__(self):
        self.activate: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.activate.append(ws)
        logger.info("client connected")
        await ws.send_json(history.getHistory(dataRatio))

    async def disconnect(self, ws):
        self.activate.remove(ws)
        logger.info("client disconnected")

    async def broadcast(self, msg: dict):
        for connection in self.activate:
            try:
                await connection.send_json(msg)
            except:
                self.activate.remove(connection)

discord_channels = []
mqtt_client = mqtt.Client()
