import numpy as np
from dependencies import (ratio, threshold, sample_rate,  warnings, station_config, rtm_data, mqtt_client, last_interest, dmc, warning_data, 
                          add_to_buffer, add_to_quake_buffer, get_buffer, reset_quake_buffer)
from obspy.signal.trigger import classic_sta_lta, recursive_sta_lta, trigger_onset
from obspy import Trace
import json
import worker.filter as filter
import worker.report as report
import logger
import time

warnings_lock = False
warnings_update = False
last_warning_time = 0
COOL_DOWN_TIME = 20

def run_alert_tests(station_id: str, data: np.ndarray, interest=0, previous_data: np.ndarray = np.array([0, 0, 0])) -> tuple[list, int, np.ndarray]:
    """
    Check if the alert condition is met based on the given data.
    Args:
        data (list or np.ndarray): Input data to evaluate.

    Returns:
        run_alert_tests (tuple[bool, int]): A tuple where the first element is a boolean indicating if the alert condition is met, and the second element is the final interest value.
    """
    interest_result = run_interest(data, interest, previous_data)
    samples = data.shape[0]
    buffer = add_to_buffer(station_id, data)
    data = filter.filter_data(data, 3, 13.5)
    r_sta_lta_result = None
    sta_lta_result = None
    if buffer.shape[0] > 1000:
        r_sta_lta_result = run_r_sta_lta(buffer, sampling_rate=sample_rate, samples=samples)
        sta_lta_result = run_sta_lta(buffer, sampling_rate=sample_rate, samples=samples)
    result = [interest_result[0], r_sta_lta_result, sta_lta_result]

    return (result, interest_result[1], interest_result[2])


def run_r_sta_lta(data: np.ndarray, sampling_rate=100, samples: int = 100) -> bool:
    """
    Calculate the STA/LTA interest value based on the given data.
    Args:
        data (list or np.ndarray): Input data to evaluate.
    Returns:
        run_r_sta_lta (bool): A boolean indicating if the alert condition is met.
    """
    trace_x = Trace(data=data[:, 0]*ratio,header={'sampling_rate': sampling_rate})
    trace_y = Trace(data=data[:, 1]*ratio,header={'sampling_rate': sampling_rate})
    trace_z = Trace(data=data[:, 2]*ratio,header={'sampling_rate': sampling_rate})
    sta_lta_ratio_x = recursive_sta_lta(trace_x.data, int(1 * trace_x.stats.sampling_rate), int(10 * trace_x.stats.sampling_rate))[-samples:]
    sta_lta_ratio_y = recursive_sta_lta(trace_y.data, int(1 * trace_y.stats.sampling_rate), int(10 * trace_y.stats.sampling_rate))[-samples:]
    sta_lta_ratio_z = recursive_sta_lta(trace_z.data, int(1 * trace_z.stats.sampling_rate), int(10 * trace_z.stats.sampling_rate))[-samples:]
    trigger_x = trigger_onset(sta_lta_ratio_x, 3.5, 1.0)
    trigger_y = trigger_onset(sta_lta_ratio_y, 3.5, 1.0)
    trigger_z = trigger_onset(sta_lta_ratio_z, 3.5, 1.0)
    return any([len(trigger_x) > 0, len(trigger_y) > 0, len(trigger_z) > 0])


def run_sta_lta(data: np.ndarray, sampling_rate=100, samples: int = 100) -> bool:
    """
    Calculate the STA/LTA interest value based on the given data.
    Args:
        data (list or np.ndarray): Input data to evaluate.
    Returns:
        run_sta_lta (bool): A boolean indicating if the alert condition is met.
        a boolean indicating if the alert condition is met, and the second element is the final interest value.
    """
    trace_x = Trace(data=data[:, 0]*ratio,header={'sampling_rate': sampling_rate})
    trace_y = Trace(data=data[:, 1]*ratio,header={'sampling_rate': sampling_rate})
    trace_z = Trace(data=data[:, 2]*ratio,header={'sampling_rate': sampling_rate})
    sta_lta_ratio_x = classic_sta_lta(trace_x.data, int(1 * trace_x.stats.sampling_rate), int(10 * trace_x.stats.sampling_rate))[-samples:]
    sta_lta_ratio_y = classic_sta_lta(trace_y.data, int(1 * trace_y.stats.sampling_rate), int(10 * trace_y.stats.sampling_rate))[-samples:]
    sta_lta_ratio_z = classic_sta_lta(trace_z.data, int(1 * trace_z.stats.sampling_rate), int(10 * trace_z.stats.sampling_rate))[-samples:]
    trigger_x = trigger_onset(sta_lta_ratio_x, 3.5, 1.0)
    trigger_y = trigger_onset(sta_lta_ratio_y, 3.5, 1.0)
    trigger_z = trigger_onset(sta_lta_ratio_z, 3.5, 1.0)
    return any([len(trigger_x) > 0, len(trigger_y) > 0, len(trigger_z) > 0])


def run_interest(data: np.ndarray, interest=0, previous_data: np.ndarray = np.array([0, 0, 0])) -> tuple[bool, int, np.ndarray]:
    """
    Calculate the interest value based on the given data.
    Args:
        data (list or np.ndarray): Input data to evaluate.
        interest (int): The initial interest value.
        previous_data (np.ndarray): The previous data points.

    Returns:
        run_interest (tuple[bool, int]): A tuple where the first element is a boolean indicating if the alert condition is met, and the second element is the final interest value.
    """
    scaled_data = data[:, :3] * ratio
    diffs = np.diff(scaled_data, axis=0, prepend=previous_data)
    distances = np.sqrt(np.einsum("ij,ij->i", diffs, diffs))  # sqrt(x^2 + y^2 + z^2)
    it = np.empty(len(distances), dtype=np.int32)

    for idx, dist in enumerate(distances):
        if dist >= threshold:
            interest += 1
        elif interest > 1:
            interest -= 1
        else:
            interest = 0
        it[idx] = interest
    trigger = trigger_onset(np.array(it), 6, 0)
    return (len(trigger) > 0, interest, scaled_data[-1])

async def clean_warning_data():
    for station in warnings:
        if time.time() - warnings[station]["timestamp"] > 30:
            warnings.pop(station, None)

async def alert_check(client_id: str, data: np.ndarray) -> tuple[list, int, np.ndarray]:  # data = 3d array
    """run alert tests and handle exceptions

    Args:
        client_id (str): station id
        data (np.ndarray): 3 x n array of raw data

    Returns:
        tuple[list, int, np.ndarray]: (result list, processed interest, last data)
    """
    global last_interest, warnings_lock, warnings_update,  warning_data, last_warning_time
    try:
        result, interest, prev_data =  run_alert_tests(client_id, data, last_interest.get(client_id, 0), previous_data.get(client_id)) # type: ignore
    except Exception as e:
        logger.error(f"Error in alert_check: {e}")
        result, interest, prev_data = [], 0, np.array([])
    return (result, interest, prev_data)


async def alert_flow(client_id:str, data:np.ndarray, interest:int, result:list):
    global warnings_lock, last_warning_time, warnings_lock, warnings_update
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
        try:
            await dmc.add_warning(warnings, result)
        except:
            logger.warning("Error sending to discord")
    else:
        add_to_quake_buffer(client_id, data*ratio)
        if any(rtm_data.get(station, (0.0, 0.0))[0] - warning_data["prev_pgs"][0] > 5 or rtm_data.get(station, (0.0, 0.0))[1] - warning_data["prev_pgs"][1] > 5 for station in warnings):
            warnings_update = True
    if warnings_update:
        warnings_update = False
        try:
            await dmc.edit_warning_data(warnings, result)
        except:
            logger.warning("Error editing on discord")
async def normal_flow(client_id:str, data:np.ndarray):
    global warnings_lock, last_warning_time
    if (time.time() - last_warning_time) < COOL_DOWN_TIME:
        add_to_quake_buffer(client_id, data*ratio)
    else:
        if warnings_lock:
            warnings_lock = False
            try:
                await dmc.send_plot()
            except:
                logger.warning("Error sending to discord")
            report.generate_report(warning_data)
            warnings.clear()
            reset_quake_buffer()