
import numpy as np
import pandas as pd
import bisect
from typing import List, Tuple, Generator, Optional

class SlidingWindowDataset:
    """
    Pure Numpy implementation of a sliding window dataset.
    Handles mapping a global index to specific windows across discontinuous segments.
    """
    def __init__(self, 
        data_segments: List[Tuple[np.ndarray, np.ndarray]], 
        window_size_ms: float, 
        step_size_ms: float, 
        fs: float
    ):
        self.fs = fs
        self.window_samples = int(window_size_ms * fs / 1000)
        self.step_samples = int(step_size_ms * fs / 1000)
        
        self.segments = []
        self.segment_offsets = [0]
        
        current_offset = 0
        
        for X, y in data_segments:
            n_samples = X.shape[0]
            
            if n_samples < self.window_samples:
                continue
                
            n_windows = (n_samples - self.window_samples) // self.step_samples + 1
            
            self.segments.append((X, y))
            current_offset += n_windows
            self.segment_offsets.append(current_offset)
            
        self.total_windows = current_offset

    def __len__(self):
        return self.total_windows

    def __getitem__(self, idx: int) -> Tuple[np.ndarray, np.ndarray]:
        """Returns a single window (Samples x Channels) and its label."""
        if idx >= self.total_windows or idx < 0:
            raise IndexError("Index out of bounds")

        segment_idx = bisect.bisect_right(self.segment_offsets, idx) - 1
        
        local_idx = idx - self.segment_offsets[segment_idx]

        start_sample = local_idx * self.step_samples
        end_sample = start_sample + self.window_samples
        
        X_segment, y_segment = self.segments[segment_idx]
        
        return X_segment[start_sample:end_sample], y_segment[end_sample - 1]

    def batch_generator(self, batch_size: int, shuffle: bool = True) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """
        Yields batches of data as (Batch_Size, Window_Len, Channels).
        Replaces the PyTorch DataLoader.
        """
        indices = np.arange(self.total_windows)
        if shuffle:
            np.random.shuffle(indices)
            
        for start_idx in range(0, self.total_windows, batch_size):
            end_idx = min(start_idx + batch_size, self.total_windows)
            batch_indices = indices[start_idx:end_idx]
            
            X_batch = []
            y_batch = []
            
            for idx in batch_indices:
                X, y = self.__getitem__(idx)
                X_batch.append(X)
                y_batch.append(y)
                
            yield np.array(X_batch), np.array(y_batch)
        

class MovementModeDataset(SlidingWindowDataset):
    """
    Extracts specific movement modes (e.g., Walking) from raw DataFrames
    and prepares them for sliding window processing.
    """
    def __init__(self, 
        df: pd.DataFrame, 
        target_mode: int, 
        feature_cols: List[str], 
        label_col: str,
        window_size_ms: float = 1000.0,
        step_size_ms: float = 100.0,
        fs: float = 500.0
    ):
        processed_segments = []

        df_ops = df.copy()
        df_ops['group_id'] = (df_ops['Mode'] != df_ops['Mode'].shift()).cumsum()
        
        mode_df = df_ops[df_ops['Mode'] == target_mode]
        
        for _, group in mode_df.groupby('group_id'):
            
            X = group[feature_cols].values
            y = group[label_col].values
            
            if len(X) > 0 and not np.isnan(X).any():
                processed_segments.append((X, y))
        
        super().__init__(processed_segments, window_size_ms, step_size_ms, fs)


class MultiModeDataset(SlidingWindowDataset):
    """
    Processes all movement modes from raw DataFrames for multi-class classification.
    Creates sliding windows for each mode segment.
    
    Args:
        df: DataFrame containing EMG data and Mode labels
        feature_cols: List of EMG channel names to use as features (e.g., ['TA', 'MG', 'RF'])
        label_col: Column name containing mode labels (e.g., 'Mode')
        window_size_ms: Window size in milliseconds
        step_size_ms: Step size for sliding window in milliseconds
        fs: Sampling frequency in Hz
    """
    def __init__(self, 
        df: pd.DataFrame, 
        feature_cols: List[str], 
        label_col: str,
        group_col: Optional[str] = None,
        window_size_ms: float = 200.0,
        step_size_ms: float = 50.0,
        fs: float = 250.0
    ):
        processed_segments = []

        # Create segments based on group_col if provided, else label_col
        # We need to ensure we split on changes in this column
        segment_key = group_col if group_col else label_col
        
        df_ops = df.copy()
        df_ops['group_id'] = (df_ops[segment_key] != df_ops[segment_key].shift()).cumsum()
        
        # Process each continuous mode segment
        for _, group in df_ops.groupby('group_id'):
            # Extract features (EMG channels only)
            X = group[feature_cols].values
            # Extract labels (Mode)
            y = group[label_col].values
            
            # Only add segments with valid data
            if len(X) > 0 and not np.isnan(X).any() and not np.isnan(y).any():
                processed_segments.append((X, y))
        
        super().__init__(processed_segments, window_size_ms, step_size_ms, fs)
            