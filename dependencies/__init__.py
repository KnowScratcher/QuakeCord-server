from .config import *
from .connections import *
from .filters import *
from .buffer import *
from .discord_message import *
import paho.mqtt.client as mqtt
import paho.mqtt.enums as mqttApi

manager = ConnectionManager()
""" Websocket manager"""

def on_connect(client, userdata, flags, rc, properties=None):
    """
    rc (return code) values:
    0: Connection successful (Authenticated)
    1: Connection refused - incorrect protocol version
    2: Connection refused - invalid client identifier
    3: Connection refused - server unavailable
    4: Connection refused - bad username or password
    5: Connection refused - not authorized
    """
    if rc == 0:
        print("✅ Authentication Successful! Connected to broker.")
    elif rc == 4 or rc == 5:
        print("❌ Authentication Failed: Check username and password.")
    else:
        print(f"❓ Connection failed with code {rc}")

mqtt_client = mqtt.Client(mqttApi.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
""" MQTT client """
mqtt_client.username_pw_set(config.get(
    "username", ""), config.get("password", ""))
mqtt_client.connect(config.get("host", "localhost"), config.get(
    "port", 1883), config.get("keepalive", 60))

__all__ = ["basePath", "dataPath", "reportPath", "dataRatio", "lastCountTime", "ratio", "threshold",
           "sample_rate", "station_config", "STATION_SECRETS", "config", "ConnectionManager", "discord_channels", "DiscordMessageControl", "manager", "mqtt_client",
           "butter_bandpass", "butter_bandpass_filter", "add_to_buffer", "add_to_quake_buffer", "clean_buffer", "build_warning_embed", "build_end_embed", "create_quake_plot", "reset_quake_buffer", "get_buffer", "get_quake_buffer"]
