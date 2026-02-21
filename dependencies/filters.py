from scipy.signal import butter, filtfilt

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


