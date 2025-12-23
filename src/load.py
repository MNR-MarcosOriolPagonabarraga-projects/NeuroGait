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
    
    # Standard mapping based on ENABL3S documentation and user file structure
    DEFAULT_CHANNEL_MAP = {
        # EMG Shank & Thigh (Sensors)
        'TA': 'Right_TA',           # Tibialis Anterior
        'MG': 'Right_MG',           # Medial Gastrocnemius
        'SOL': 'Right_SOL',         # Soleus
        'RF': 'Right_RF',           # Rectus Femoris
        'VL': 'Right_VL',           # Vastus Lateralis
        'BF': 'Right_BF',           # Biceps Femoris
        'ST': 'Right_ST',           # Semitendinosus
        
        # Kinematics (Ground Truth Labels)
        'Ankle_Angle': 'Right_Ankle_Angle',
        'Knee_Angle': 'Right_Knee_Angle',
        
        # Discrete Events (Triggers)
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
        
        # Validate path existence
        if not os.path.exists(self.root_path):
            logger.error(f"Root path does not exist: {self.root_path}")
            raise FileNotFoundError(f"Root path not found: {self.root_path}")

    def _get_file_path(self, circuit_id: int, file_type: str = 'raw') -> str:
        """Constructs the file path following ENABL3S naming convention."""
        # Naming convention: AB156_Circuit_001_raw.csv
        filename = f"{self.subject_id}_Circuit_{circuit_id:03d}_{file_type}.csv"
        
        # Folder convention: Raw or Processed (Capitalized in your tree structure)
        folder_name = "Raw" if file_type.lower() == 'raw' else "Processed"
        
        return os.path.join(self.root_path, folder_name, filename)

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

        # Map requested abstract names to actual CSV headers
        usecols = None
        valid_keys = []
        
        if requested_channels:
            valid_keys = [k for k in requested_channels if k in self.channel_map]
            missing_keys = set(requested_channels) - set(valid_keys)
            
            if missing_keys:
                logger.warning(f"Requested channels not in map: {missing_keys}")
            
            usecols = [self.channel_map[k] for k in valid_keys]

        try:
            # Memory Optimization: Load ONLY specific columns
            df = pd.read_csv(file_path, usecols=usecols)
            
            # Rename columns back to abstract names (e.g., 'Right_TA' -> 'TA')
            if requested_channels:
                reverse_map = {v: k for k, v in self.channel_map.items() if k in valid_keys}
                df.rename(columns=reverse_map, inplace=True)
                
            return df
            
        except ValueError as e:
            logger.error(f"Column mismatch in file {filename}. Error: {e}")
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
                # Add metadata column for debugging
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
            
        # Vectorized operation using NumPy for performance
        # If Angle > threshold -> Swing (1), else Stance (0)
        df['Label_Phase'] = np.where(df[angle_col] > threshold, 1, 0)
        
        logger.info(f"Labels generated. Distribution: {df['Label_Phase'].value_counts().to_dict()}")
        return df

# ==========================================
# Usage Example (Copy this to your main script)
# ==========================================
if __name__ == "__main__":
    # 1. Configuration
    PATH_ROOT = '/home/marcos/Downloads/5362627'  # Update this path
    SUBJECT = 'AB156'
    
    # 2. Define sensors for the Low-Resource Model
    # We load TA, MG, RF for input, and Ankle_Angle for Ground Truth
    SENSOR_CONFIG = ['TA', 'MG', 'RF', 'Ankle_Angle']
    
    # 3. Initialize Loader
    loader = Enabl3sDataLoader(PATH_ROOT, SUBJECT)
    
    # 4. Load Training Batch (e.g., first 5 circuits)
    df_train = loader.load_dataset_batch(range(1, 6), config=SENSOR_CONFIG)
    
    # 5. Generate Labels (Cross-Modal Learning)
    # Using Ankle Angle to create binary labels (0=Stance, 1=Swing)
    df_train = loader.add_gait_phase_label(df_train, angle_col='Ankle_Angle', threshold=2.0)
    
    # 6. Preview Data
    if not df_train.empty:
        print("\n--- Data Preview ---")
        print(df_train.head())
    else:
        print("Failed to load data.")