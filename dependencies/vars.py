import time
import asyncio
from collections import defaultdict
from .discord_message import DiscordMessageControl
from .connections import discord_channels

rtm_data = {}
station_queues = defaultdict(asyncio.Queue)
dmc = DiscordMessageControl(discord_channels)
warnings = {}
warning_data = {
    "prev_pgs": (0.0, 0.0),
    "prev_result": [False] * 3,
    "warnings": warnings,
    "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
}
last_interest = {}