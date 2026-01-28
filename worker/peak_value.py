from matplotlib import pyplot as plt
from scipy.signal import butter, filtfilt
import numpy

def butter_bandpass(lowcut, highcut, fs, order=5):
    """
    Designs a Butterworth bandpass filter.

    Args:
        lowcut (float): The lower cutoff frequency of the bandpass filter (Hz).
        highcut (float): The upper cutoff frequency of the bandpass filter (Hz).
        fs (float): The sampling rate of the signal (Hz).
        order (int): The order of the filter. Higher orders result in steeper roll-off.

    Returns:
        tuple: A tuple (b, a) representing the numerator (b) and denominator (a)
               polynomials of the IIR filter.
    """
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band') # type: ignore
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    """
    Applies a Butterworth bandpass filter to the input data.

    Args:
        data (numpy.ndarray): The input signal to be filtered.
        lowcut (float): The lower cutoff frequency of the bandpass filter (Hz).
        highcut (float): The upper cutoff frequency of the bandpass filter (Hz).
        fs (float): The sampling rate of the signal (Hz).
        order (int): The order of the filter.

    Returns:
        numpy.ndarray: The filtered signal.
    """
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    # filtfilt applies the filter forward and backward to avoid phase distortion
    y = filtfilt(b, a, data)
    return y

ratio = 980/8028.6
# --- Filter Parameters ---
sample_rate = 100  # Hz (This is your specified sample rate)
low_cutoff = 2  # Hz
high_cutoff = 20  # Hz
filter_order = 7  # A common choice for filter order
def get_filtered_peak_value(d) -> tuple:
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
