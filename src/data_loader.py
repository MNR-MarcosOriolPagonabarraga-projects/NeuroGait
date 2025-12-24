import os
import pandas as pd
import numpy as np
import logging
from typing import List, Optional, Union, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class Enabl3sDataLoader:
    """
    Production-ready data loader for the ENABL3S dataset.
    
    Designed for Cross-Modal Learning workflows:
    - Efficiently loads 'Raw' CSV files using column pruning.
    - Handles sensor mapping abstraction (Muscle Name -> CSV Column).
    - Supports batch loading for training sets.
    """
    
    DEFAULT_CHANNEL_MAP = {
        'TA': 'Right_TA',           # Tibialis Anterior
        'MG': 'Right_MG',           # Medial Gastrocnemius
        'SOL': 'Right_SOL',         # Soleus
        'RF': 'Right_RF',           # Rectus Femoris
        'VL': 'Right_VL',           # Vastus Lateralis
        'BF': 'Right_BF',           # Biceps Femoris
        'ST': 'Right_ST',           # Semitendinosus
        
        'Ankle_Angle': 'Right_Ankle',
        'Knee_Angle': 'Right_Knee',
        
        'Heel_Strike': 'Right_Heel_Contact',
        'Toe_Off': 'Right_Toe_Off'
    }

    def __init__(self, root_path: str, subject_id: str, custom_map: Optional[Dict[str, str]] = None):
        """
        Initialize the loader.

        Args:
            root_path (str): Absolute path to the dataset root (e.g., '/data/AB156').
            subject_id (str): Subject identifier (e.g., 'AB156').
            custom_map (dict, optional): Override default channel mapping if necessary.
        """
        self.root_path = root_path
        self.subject_id = subject_id
        self.channel_map = custom_map if custom_map else self.DEFAULT_CHANNEL_MAP
        
        if not os.path.exists(self.root_path):
            logger.error(f"Root path does not exist: {self.root_path}")
            raise FileNotFoundError(f"Root path not found: {self.root_path}")

    def _get_file_path(self, circuit_id: int, file_type: str = 'raw') -> str:
        """Constructs the file path following ENABL3S naming convention."""
        filename = f"{self.subject_id}_Circuit_{circuit_id:03d}_{file_type}.csv"
        folder_name = "Raw" if file_type.lower() == 'raw' else "Processed"
        
        return os.path.join(self.root_path, self.subject_id, folder_name, filename)

    def load_circuit(self, circuit_id: int, requested_channels: Optional[List[str]] = None, file_type: str = 'raw') -> pd.DataFrame:
        """
        Loads a single circuit trial from disk with memory optimization.

        Args:
            circuit_id (int): The circuit number (e.g., 1).
            requested_channels (list): List of abstract names (e.g., ['TA', 'MG']).
                                       If None, loads all columns.
            file_type (str): 'raw' or 'processed'.

        Returns:
            pd.DataFrame: Loaded data with normalized column names, or empty DataFrame on failure.
        """
        file_path = self._get_file_path(circuit_id, file_type)
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found for Circuit {circuit_id}: {file_path}")
            return pd.DataFrame()

        usecols = None
        valid_keys = []
        
        if requested_channels:
            valid_keys = [k for k in requested_channels if k in self.channel_map]
            missing_keys = set(requested_channels) - set(valid_keys)
            
            if missing_keys:
                logger.warning(f"Requested channels not in map: {missing_keys}")
            
            usecols = [self.channel_map[k] for k in valid_keys]

        try:
            df = pd.read_csv(file_path, usecols=usecols)
            
            if requested_channels:
                reverse_map = {v: k for k, v in self.channel_map.items() if k in valid_keys}
                df.rename(columns=reverse_map, inplace=True)
                
            return df
            
        except ValueError as e:
            logger.error(f"Column mismatch in file {file_path}. Error: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.critical(f"Unexpected error loading Circuit {circuit_id}: {e}")
            return pd.DataFrame()

    def load_dataset_batch(self, circuit_range: range, config: List[str]) -> pd.DataFrame:
        """
        Loads multiple circuits and concatenates them into a single training set.

        Args:
            circuit_range (range): Range of circuits to load (e.g., range(1, 11)).
            config (list): List of channels to load.

        Returns:
            pd.DataFrame: Concatenated dataset.
        """
        data_frames = []
        logger.info(f"Starting batch load: Circuits {circuit_range.start} to {circuit_range.stop - 1}...")
        
        for cid in circuit_range:
            df = self.load_circuit(cid, requested_channels=config)
            
            if not df.empty:
                df['Circuit_ID'] = cid
                data_frames.append(df)
            else:
                logger.debug(f"Skipping empty/missing Circuit {cid}")
        
        if not data_frames:
            logger.error("No data loaded. Check paths or circuit IDs.")
            return pd.DataFrame()
            
        full_df = pd.concat(data_frames, ignore_index=True)
        logger.info(f"Batch load complete. Total Shape: {full_df.shape}")
        return full_df

    def add_gait_phase_label(self, df: pd.DataFrame, angle_col: str = 'Ankle_Angle', threshold: float = 0.0) -> pd.DataFrame:
        """
        Feature Engineering: Generates Ground Truth labels based on kinematics.
        
        Labels:
            0: Stance Phase (Stable/Plantarflexion)
            1: Swing Phase (Dorsiflexion / Lifting)
            
        Args:
            df (pd.DataFrame): The dataset containing the angle column.
            angle_col (str): The name of the angle column in the DataFrame.
            threshold (float): Angle threshold in degrees to trigger Swing phase.

        Returns:
            pd.DataFrame: Dataset with new 'Label_Phase' column.
        """
        if df.empty:
            return df

        if angle_col not in df.columns:
            logger.error(f"Cannot label data: Column '{angle_col}' missing.")
            return df
            
        baseline = df[angle_col].median()
        centered_angle = df[angle_col] - baseline
        
        threshold = np.percentile(centered_angle, 75)
        df['Label_Phase'] = np.where(centered_angle > threshold, 1, 0)
        
        swing_ratio = df['Label_Phase'].mean() * 100
        logger.info(f"Labels generated (Percentile-75). Threshold: {threshold:.4f}. Swing Ratio: {swing_ratio:.2f}%")
        return df