import numpy as np
from dependencies import butter_bandpass_filter, sample_rate


def filter_data(data: np.ndarray, low: float = 2, high: float = (sample_rate//2-0.1), order: int = 7) -> np.ndarray:  # 3d array
    return np.array([
        butter_bandpass_filter(data[:, 0], low, high, sample_rate, order=order),
        butter_bandpass_filter(data[:, 1], low, high, sample_rate, order=order),
        butter_bandpass_filter(data[:, 2], low, high, sample_rate, order=order)
    ]).T
