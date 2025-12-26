import os
import pandas as pd
import numpy as np
import logging
from typing import List, Optional, Dict

from .utils import resample_df

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
        'Toe_Off': 'Right_Toe_Off',
        
        # Activity Mode for hierarchical control
        'Mode': 'Mode'
    }

    def __init__(self, root_path: str, subject_id: str, custom_map: Optional[Dict[str, str]] = None, target_fs: Optional[float] = None):
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
        self.original_fs = 1000.0 # Hz
        self.target_fs = target_fs
    
        # Load Metadata
        metadata_path = os.path.join(self.root_path, self.subject_id, f"{self.subject_id}_Metadata.csv")
        self.metadata = pd.read_csv(metadata_path)
        self.metadata['Filename'] = self.metadata['Filename'].str.strip()


    def _get_file_path(self, circuit_id: int, file_type: str = 'raw') -> str:
        """Constructs the file path following ENABL3S naming convention."""
        if file_type.lower() == 'raw':
            filename = f"{self.subject_id}_Circuit_{circuit_id:03d}_raw.csv"
            folder_name = "Raw"
        elif file_type.lower() in ['processed', 'post']:
            filename = f"{self.subject_id}_Circuit_{circuit_id:03d}_post.csv"
            folder_name = "Processed"
        else:
            filename = f"{self.subject_id}_Circuit_{circuit_id:03d}_{file_type}.csv"
            folder_name = "Raw"
        
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

        usecols = None
        valid_keys = []
        
        if requested_channels:
            valid_keys = [k for k in requested_channels if k in self.channel_map]
            
            try:
                header = pd.read_csv(file_path, nrows=0).columns.tolist()
                wanted_raw = [self.channel_map[k] for k in valid_keys]
                usecols = [c for c in wanted_raw if c in header]
                
                missing = set(wanted_raw) - set(usecols)
                if missing:
                    logger.debug(f"Missing optional columns in {file_path}: {missing}")
                     
            except Exception as e:
                logger.error(f"Failed to read header of {file_path}: {e}")
                return pd.DataFrame()

        try:
            df = pd.read_csv(file_path, usecols=usecols)

            if not df.empty and isinstance(df.index, pd.RangeIndex):
                df.index = pd.to_timedelta(df.index / self.original_fs, unit='s')
            
            if requested_channels:
                reverse_map = {v: k for k, v in self.channel_map.items() if k in valid_keys}
                df.rename(columns=reverse_map, inplace=True)

            return df
            
        except ValueError as e:
            logger.error(f"Column mismatch in file {file_path}. Error: {e}")
            return pd.DataFrame()


    def load_dataset_batch(self, circuit_range: range, channels: List[str]) -> pd.DataFrame:
        """
        Loads multiple circuits and concatenates them into a single training set.
        
        Args:
            circuit_range (range): Range of circuits to load (e.g., range(1, 11)).
            channels (list): List of channels to load.

        Returns:
            pd.DataFrame: Concatenated dataset.
        """
        data_frames = []
        logger.info(f"Starting batch load: Circuits {circuit_range.start} to {circuit_range.stop - 1}...")
        
        for cid in circuit_range:
            if not self.metadata.empty:
                df = self.load_calibrated_circuit(cid, requested_channels=channels)
            else:
                df = self.load_circuit(cid, requested_channels=channels)
            
            if df is not None and not df.empty:
                df['Circuit_ID'] = cid
                df = self.add_gait_phase_label(df, circuit_id=cid)
                if self.target_fs:
                    df = resample_df(df, self.target_fs, 'Label_Phase')

                data_frames.append(df)
            else:
                logger.debug(f"Skipping empty/bad Circuit {cid}")
        
        if not data_frames:
            logger.error("No data loaded. Check paths or circuit IDs.")
            return pd.DataFrame()
            
        full_df = pd.concat(data_frames, ignore_index=True)
        logger.info(f"Batch load complete. Total Shape: {full_df.shape}")
        return full_df

    def load_calibrated_circuit(self, circuit_id: int, requested_channels: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        Loads a circuit and applies patient-specific calibration (Drift Removal).
        
        Args:
            circuit_id (int): Circuit ID.
            requested_channels (list): Channels to load.
            
        Returns:
            pd.DataFrame: Calibrated dataframe, or None if skipped (e.g. 'trip' in notes).
        """
        file_id = f"{self.subject_id}_Circuit_{circuit_id:03d}"
        
        if self.metadata.empty:
            return self.load_circuit(circuit_id, requested_channels)
             
        meta_row = self.metadata[self.metadata['Filename'] == file_id]
        if meta_row.empty:
            logger.warning(f"No metadata for {file_id}")
            return self.load_circuit(circuit_id, requested_channels)
            
        meta = meta_row.iloc[0]

        req = set(requested_channels) if requested_channels else set(self.channel_map.keys())
        df = self.load_circuit(circuit_id, list(req))
        if df.empty: 
            return None

        if 'Right_Knee' in df.columns:
            col_name = 'Knee_Angle' if 'Knee_Angle' in df.columns else None
            if col_name:
                k_min, k_max = meta['R Knee Min'], meta['R Knee Max']
                if k_max != k_min:
                    df['Knee_Norm'] = (df[col_name] - k_min) / (k_max - k_min)
                else:
                    df['Knee_Norm'] = 0

        col_name = 'Ankle_Angle' if 'Ankle_Angle' in df.columns else None
        if col_name:
            a_min, a_max = meta['R Ankle Min'], meta['R Ankle Max']
            if a_max != a_min:
                df['Ankle_Norm'] = (df[col_name] - a_min) / (a_max - a_min)
            else:
                df['Ankle_Norm'] = 0
                 
        return df
    
    def _events_to_labels(self, n_samples: int, heel_contacts: np.ndarray,   toe_offs: np.ndarray) -> np.ndarray:
        """
        Converts event indices to continuous binary labels.
        
        Gait cycle: Heel Contact (start of Stance) -> Toe Off (start of Swing) -> next Heel Contact
        
        Args:
            n_samples: Total number of samples
            heel_contacts: Array of heel contact indices (start of Stance)
            toe_offs: Array of toe off indices (start of Swing)
            
        Returns:
            Binary labels: 0=Swing, 1=Stance
        """
        labels = np.zeros(n_samples, dtype=int)
        
        events = []
        for hc in heel_contacts:
            if not np.isnan(hc) and 0 <= hc < n_samples:
                events.append((int(hc), 1))  # Stance starts
        for to in toe_offs:
            if not np.isnan(to) and 0 <= to < n_samples:
                events.append((int(to), 0))  # Swing starts
        
        events.sort()
        
        current_phase = 0
        for i, (idx, phase) in enumerate(events):
            if i < len(events) - 1:
                next_idx = events[i + 1][0]
                labels[idx:next_idx] = phase
                current_phase = phase
            else:
                labels[idx:] = phase
        
        return labels

    def add_gait_phase_label(self, df: pd.DataFrame, circuit_id: Optional[int] = None) -> pd.DataFrame:
        """
        Feature Engineering: Generates Robust Ground Truth labels.
        
        Logic:
        1. Load processed file with event indices if circuit_id provided -> Gold Standard.
        2. Use Hardware Switches (Toe_Off) if available in raw data.
        3. Else, use Calibrated Kinematics (Knee_Norm > 0.75 -> Swing).
        
        Args:
            df (pd.DataFrame): The dataset (must include 'Toe_Off' or 'Knee_Norm').
            circuit_id (int, optional): Circuit ID to load event data from processed files.

        Returns:
            pd.DataFrame: Dataset with 'Label_Phase' column (0=Stance, 1=Swing).
        """
        if circuit_id is not None:
            try:
                df_processed = self.load_circuit(circuit_id, file_type='post')
                if not df_processed.empty and 'Right_Heel_Contact' in df_processed.columns and 'Right_Toe_Off' in df_processed.columns:
                    heel_contacts = df_processed['Right_Heel_Contact'].values
                    toe_offs = df_processed['Right_Toe_Off'].values
                    
                    df['Label_Phase'] = self._events_to_labels(len(df), heel_contacts, toe_offs)
                    method = "Processed Events (Heel Contact + Toe Off)"
                    swing_ratio = df['Label_Phase'].mean() * 100
                    logger.info(f"Labels generated via {method}. Swing Ratio: {swing_ratio:.2f}%")
                    return df
            except Exception as e:
                logger.warning(f"Could not load processed file for circuit {circuit_id}: {e}. Falling back.")
        
        if df is None:
            return None
        
        if 'Toe_Off' in df.columns:
            df['Label_Phase'] = df['Toe_Off'].fillna(0).astype(int)
            method = "Hardware (Toe_Off)"
            
        elif 'Knee_Norm' in df.columns:
            df['Label_Phase'] = np.where(df['Knee_Norm'] > 0.75, 1, 0)
            method = "Calibrated Kinematics (Knee > 0.75)"
            
        else:
            if 'Ankle_Angle' in df.columns:
                threshold = np.percentile(df['Ankle_Angle'], 80)
                df['Label_Phase'] = np.where(df['Ankle_Angle'] > threshold, 1, 0)
                method = "Legacy Percentile (Ankle)"
            else:
                df['Label_Phase'] = 0
                method = "Default (All Stance)"
        
        swing_ratio = df['Label_Phase'].mean() * 100
        logger.info(f"Labels generated via {method}. Swing Ratio: {swing_ratio:.2f}%")
        return df