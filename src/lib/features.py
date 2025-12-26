import numpy as np

def extract_mav(signal):
    """Calculate Mean Absolute Value (MAV) of a signal.
    Args:
        signal: 1D numpy array representing a signal channel
    Returns:
        float: Mean absolute value
    """
    return np.mean(np.abs(signal))


def extract_rms(signal):
    """Calculate Root Mean Square (RMS) of a signal.
    Args:
        signal: 1D numpy array representing a signal channel
    Returns:
        float: Root mean square value
    """
    return np.sqrt(np.mean(signal ** 2))


def extract_wl(signal):
    """Calculate Waveform Length (WL) of a signal.
    Args:
        signal: 1D numpy array representing a signal channel
    Returns:
        float: Waveform length (sum of absolute differences)
    """
    return np.sum(np.abs(np.diff(signal)))


def extract_statistical_features(window):
    """Extract MAV, RMS, and WL features from each EMG channel in a window.
    
    This function extracts three statistical features (MAV, RMS, WL) from
    each channel in the input window, concatenating them into a single
    feature vector.
    Args:
        window: 2D numpy array of shape (n_samples, n_channels)
                representing a time window of EMG data  
    Returns:
        1D numpy array: Feature vector of shape (n_channels * 3,)
                       Features are ordered as: [ch0_MAV, ch0_RMS, ch0_WL,
                                                  ch1_MAV, ch1_RMS, ch1_WL, ...]
    """
    features = []
    for ch in range(window.shape[1]):
        channel_data = window[:, ch]
        mav = extract_mav(channel_data)
        rms = extract_rms(channel_data)
        wl = extract_wl(channel_data)
        features.extend([mav, rms, wl])
    return np.array(features)


def sum_channels(window):
    """Sum EMG signals across all channels to create a single channel.
    This preprocessing step reduces multi-channel EMG to a single channel
    by summing across channels, which can simplify the input for a tiny DNN
    suitable for microcontroller deployment.
    Args:
        window: 2D numpy array of shape (n_samples, n_channels)
                representing a time window of EMG data
    Returns:
        1D numpy array: Summed signal of shape (n_samples,)
    """
    return np.sum(window, axis=1)