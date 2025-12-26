import numpy as np
from scipy import signal
from typing import Tuple

class EMGPreprocessor:
    """
    Handles signal conditioning and feature extraction for EMG signals.
    Replicates the processing chain used in the embedded firmware.
    """
    
    
    def __init__(self, fs: float = 200.0):
        self.fs = fs
        
    def apply_filter(self, data: np.ndarray) -> np.ndarray:
        """
        Applies Bandpass (20-90Hz) and Notch (50Hz) filters.
        CRITICAL: Uses CAUSAL filtering (sosfilt) to match C++ real-time implementation.
        """
        sos_bp = signal.butter(1, [20, 90], btype='bandpass', fs=self.fs, output='sos')
        filtered = signal.sosfilt(sos_bp, data, axis=0)
        b_notch, a_notch = signal.iirnotch(50, 30, self.fs)
        filtered = signal.lfilter(b_notch, a_notch, filtered, axis=0)
        
        return filtered

    def rectify(self, data: np.ndarray) -> np.ndarray:
        """Full-wave rectification."""
        return np.abs(data)

    def compute_features(self, data: np.ndarray, window_size_ms: float = 100.0, step_size_ms: float = 100.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts MAV and WL features using a sliding window.
        
        Args:
            data: Input signal (Samples x Channels)
            window_size_ms: Window length in milliseconds
            step_size_ms: Stride length in milliseconds
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (Features, Subsampled Labels/Indices if needed)
            Here we return the Feature Matrix.
        """
        window_samples = int(window_size_ms * self.fs / 1000)
        step_samples = int(step_size_ms * self.fs / 1000)
        
        n_samples, n_channels = data.shape
        n_windows = (n_samples - window_samples) // step_samples + 1
        
        features = np.zeros((n_windows, n_channels * 2))
        
        for i in range(n_windows):
            start = i * step_samples
            end = start + window_samples
            window = data[start:end, :]
            
            # Features
            mav = np.mean(window, axis=0)
            wl = np.sum(np.abs(np.diff(window, axis=0)), axis=0)
            
            feats_row = []
            for ch in range(n_channels):
                feats_row.append(mav[ch])
                feats_row.append(wl[ch])
                
            features[i, :] = np.array(feats_row)
            
        return features
