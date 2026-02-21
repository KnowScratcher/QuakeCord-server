from .config import *
from .connections import *
from .filters import *
from .buffer import *
from .discord_message import *

manager = ConnectionManager()
""" Websocket manager"""

mqtt_client = mqtt.Client()
""" MQTT client """
mqtt_client.username_pw_set(config.get(
    "username", ""), config.get("password", ""))
mqtt_client.connect(config.get("host", "localhost"), config.get(
    "port", 1883), config.get("keepalive", 60))

__all__ = ["basePath", "dataPath", "dataRatio", "lastCountTime", "ratio", "threshold",
           "sample_rate", "station_config", "STATION_SECRETS", "config", "ConnectionManager", "discord_channels", "DiscordMessageControl", "manager", "mqtt_client",
           "butter_bandpass", "butter_bandpass_filter", "add_to_buffer", "add_to_quake_buffer", "clean_buffer", "build_warning_embed", "build_end_embed", "create_quake_plot", "reset_quake_buffer", "get_buffer", "get_quake_buffer"]
