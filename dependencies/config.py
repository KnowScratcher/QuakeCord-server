import json
import os


basePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
""" The base dir """
dataPath = os.path.join(basePath, "data")
""" The data directory """
reportPath = os.path.join(basePath, "reports")
""" The report directory """
dataRatio = 980.0 / 8028.6
""" The experiment data for data -> gal """
discordPath = os.path.join(basePath, "discord_bot")

lastCountTime: dict[str, float] = {}
""" Record of the last count time of each station, this value will change about every 49 days """

ratio = 980/8028.6
""" The experiment data for data -> gal """

threshold = 1.1
""" The alert threshold ratio """

sample_rate = 100
""" The sample rate """

global station_config
with open(os.path.join(basePath, "station.json"), "r", encoding="utf-8") as f:
    station_config = json.load(f)

global STATION_SECRETS
with open(os.path.join(basePath, "secret.json"), "r", encoding="utf-8") as f:
    STATION_SECRETS = json.load(f)

global config
with open(os.path.join(basePath, "config.json"), "r", encoding="utf-8") as f:
    config = json.load(f)
