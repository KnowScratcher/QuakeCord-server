import json
import time
from dependencies import reportPath, station_config
import os


def generate_report(event_data: dict) -> None:
    """Generate detection report

    Args:
        event_data (dict): event data dictionary
        {
            'prev_pgs': (15.723041678077264, 0.4277398878472924),
            'prev_result': [True, None, None],
            'time': '2026-02-21 21:04:58',
            'warnings': {
                'TST': {
                    'lat': 23.46,
                    'lng': 120.44,
                    'pga': np.float64(15.723041678077264),
                    'pgv': np.float64(0.4277398878472924),
                    'timestamp': 1771679098.4861042
                }
            }
        }
    """
    file_name = f"report_{time.strftime('%Y%m%d_%H%M%S', time.strptime(event_data['time'], '%Y-%m-%d %H:%M:%S'))}.json"
    with open(os.path.join(reportPath, file_name), "w", encoding="utf-8") as f:
        data = {
            "time": event_data["time"] + " (UTC+8)",
            # Used for JavaScript Map markers
            "detections": [],
            "detectionType": event_data["prev_result"]
        }
        for station, warning in event_data["warnings"].items():
            station_info = station_config[station]
            data["detections"].append({
                "name": station,
                "lat": warning["lat"],
                "lng": warning["lng"],
                "elevation": station_info.get("elevation", ""),
                "sensitivity": station_info.get("sensitivity", ""),
                "pga": warning["pga"],
                "pgv": warning["pgv"],
                "timestamp": warning["timestamp"]
            })
        json.dump(data, f, indent=4)
