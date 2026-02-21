import numpy as np
from dependencies import ratio, threshold, sample_rate, butter_bandpass_filter, buffer_x, buffer_y, buffer_z, add_to_buffer
from obspy.signal.trigger import classic_sta_lta, recursive_sta_lta, trigger_onset
from obspy import Trace, Stream
import math
from matplotlib import pyplot as plt
import worker.filter as filter

def run_alert_tests(station_id: str, data: np.ndarray, interest=0) -> tuple[list, int]:
    """
    Check if the alert condition is met based on the given data.
    Args:
        data (list or np.ndarray): Input data to evaluate.

    Returns:
        run_alert_tests (tuple[bool, int]): A tuple where the first element is a boolean indicating if the alert condition is met, and the second element is the final interest value.
    """
    interest_result = run_interest(data, interest)
    samples = data.shape[0]
    buffer = add_to_buffer(station_id, data)
    data = filter.filter_data(data, 3, 13.5)
    r_sta_lta_result = None
    sta_lta_result = None
    if buffer.shape[0] > 1000:
        r_sta_lta_result = run_r_sta_lta(buffer, sampling_rate=sample_rate, samples=samples)
        sta_lta_result = run_sta_lta(buffer, sampling_rate=sample_rate, samples=samples)
    result = [interest_result[0], r_sta_lta_result, sta_lta_result]
     
    return (result, interest_result[1])

def run_r_sta_lta(data: np.ndarray, sampling_rate=100, samples: int=100) -> bool:
    """
    Calculate the STA/LTA interest value based on the given data.
    Args:
        data (list or np.ndarray): Input data to evaluate.
    Returns:
        run_r_sta_lta (bool): A boolean indicating if the alert condition is met.
    """
    trace_x = Trace(data=data[:,0]*ratio, header={'sampling_rate': sampling_rate})
    trace_y = Trace(data=data[:,1]*ratio, header={'sampling_rate': sampling_rate})
    trace_z = Trace(data=data[:,2]*ratio, header={'sampling_rate': sampling_rate})
    sta_lta_ratio_x = recursive_sta_lta(trace_x.data, int(1 * trace_x.stats.sampling_rate), int(10 * trace_x.stats.sampling_rate))[-samples:]
    sta_lta_ratio_y = recursive_sta_lta(trace_y.data, int(1 * trace_y.stats.sampling_rate), int(10 * trace_y.stats.sampling_rate))[-samples:]
    sta_lta_ratio_z = recursive_sta_lta(trace_z.data, int(1 * trace_z.stats.sampling_rate), int(10 * trace_z.stats.sampling_rate))[-samples:]
    trigger_x = trigger_onset(sta_lta_ratio_x, 3.5, 1.0)
    trigger_y = trigger_onset(sta_lta_ratio_y, 3.5, 1.0)
    trigger_z = trigger_onset(sta_lta_ratio_z, 3.5, 1.0)
    return any([len(trigger_x) > 0, len(trigger_y) > 0, len(trigger_z) > 0])

def run_sta_lta(data: np.ndarray, sampling_rate=100, samples: int=100) -> bool:
    """
    Calculate the STA/LTA interest value based on the given data.
    Args:
        data (list or np.ndarray): Input data to evaluate.
    Returns:
        run_sta_lta (bool): A boolean indicating if the alert condition is met.
        a boolean indicating if the alert condition is met, and the second element is the final interest value.
    """
    trace_x = Trace(data=data[:,0]*ratio, header={'sampling_rate': sampling_rate})
    trace_y = Trace(data=data[:,1]*ratio, header={'sampling_rate': sampling_rate})
    trace_z = Trace(data=data[:,2]*ratio, header={'sampling_rate': sampling_rate})
    sta_lta_ratio_x = classic_sta_lta(trace_x.data, int(1 * trace_x.stats.sampling_rate), int(10 * trace_x.stats.sampling_rate))[-samples:]
    sta_lta_ratio_y = classic_sta_lta(trace_y.data, int(1 * trace_y.stats.sampling_rate), int(10 * trace_y.stats.sampling_rate))[-samples:]
    sta_lta_ratio_z = classic_sta_lta(trace_z.data, int(1 * trace_z.stats.sampling_rate), int(10 * trace_z.stats.sampling_rate))[-samples:]
    trigger_x = trigger_onset(sta_lta_ratio_x, 3.5, 1.0)
    trigger_y = trigger_onset(sta_lta_ratio_y, 3.5, 1.0)
    trigger_z = trigger_onset(sta_lta_ratio_z, 3.5, 1.0)
    return any([len(trigger_x) > 0, len(trigger_y) > 0, len(trigger_z) > 0])

def run_interest(data: np.ndarray, interest=0):
    """
    Calculate the interest value based on the given data.
    Args:
        data (list or np.ndarray): Input data to evaluate.

    Returns:
        run_interest (tuple[bool, int]): A tuple where the first element is a boolean indicating if the alert condition is met, and the second element is the final interest value.
    """
    it = np.array([])
    prev_x = data[:, 0][0]*ratio
    prev_y = data[:, 1][0]*ratio
    prev_z = data[:, 2][0]*ratio
    for i, j, k in zip(data[:, 0]*ratio, data[:, 1]*ratio, data[:, 2]*ratio):
        if math.sqrt((i - prev_x)**2 + (j - prev_y)**2 + (k - prev_z)**2) >= threshold:
            # if abs(i - prev_x) >= t or abs(j - prev_y) >= t or abs(k - prev_z) >= t:
            interest += 1  # 1
        else:
            if interest > 1:
                interest -= 1
            else:
                interest = 0
        it = np.append(it, interest)
        prev_x = i
        prev_y = j
        prev_z = k
    trigger = trigger_onset(np.array(it), 6, 0)
    return (len(trigger) > 0, interest)
