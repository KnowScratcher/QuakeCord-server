from matplotlib import pyplot as plt
from scipy.signal import butter, filtfilt
import numpy
from dependencies import ratio, butter_bandpass_filter

# --- Filter Parameters ---
sample_rate = 100  # Hz (This is your specified sample rate)
low_cutoff = 2  # Hz
high_cutoff = 49.9  # Hz
filter_order = 7  # A common choice for filter order
def get_filtered_peak_value(d) -> tuple[int, int]:
    """
    get the peak value of filtered data in 2 ~ 20 Hz bandpass filter.
    Args:
        d (3d Array): x, y, z

    Returns:
        tuple: (pga, pgv)
    """
    filtered_a1 = butter_bandpass_filter(d[:,0] * ratio, low_cutoff, high_cutoff, sample_rate, order=filter_order)
    filtered_a2 = butter_bandpass_filter(d[:,1] * ratio, low_cutoff, high_cutoff, sample_rate, order=filter_order)
    filtered_a3 = butter_bandpass_filter(d[:,2] * ratio, low_cutoff, high_cutoff, sample_rate, order=filter_order)
    filtered_a = numpy.sqrt(filtered_a1**2 + filtered_a2**2 + filtered_a3**2)
    filtered_v1 = butter_bandpass_filter(numpy.cumsum(d[:,0]) * (ratio/25), low_cutoff, high_cutoff, sample_rate, order=filter_order)
    filtered_v2 = butter_bandpass_filter(numpy.cumsum(d[:,1]) * (ratio/25), low_cutoff, high_cutoff, sample_rate, order=filter_order)
    filtered_v3 = butter_bandpass_filter(numpy.cumsum(d[:,2]) * (ratio/25), low_cutoff, high_cutoff, sample_rate, order=filter_order)
    filtered_v = numpy.sqrt(filtered_v1**2 + filtered_v2**2 + filtered_v3**2)
    return max(filtered_a), max(filtered_v) # type: ignore
