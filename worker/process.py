import pandas as pd
import os
import numpy as np
import logger
from dependencies import rtm_data, lastCountTime, station_queues, warnings, last_interest
import time
import worker.peak_value as peak_value
import worker.alert as alert
from anyio import to_thread


previous_data: dict[str, np.ndarray] = {}


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
    raw_data = np.array([[i["dt"], i["x"], i["y"], i["z"]]
                        for i in data["data"]])
    try:
        rtm_data[station_id] = peak_value.get_filtered_peak_value(
            raw_data[:, 1:4])
    except Exception as e:
        logger.error(f"Error in get_filtered_peak_value: {e}")
        rtm_data[station_id] = (0.0, 0.0)
    result, interest, prev_data = await alert.alert_check(station_id, raw_data[:, 1:4])
    last_interest[station_id] = interest
    previous_data[station_id] = prev_data
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