import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from .lib.data_loader import Enabl3sDataLoader
from .lib.preprocess import EMGPreprocessor
from .lib.dataset import MultiModeDataset

# Defines the mapping for the 3 classes
PHASE_NAMES = {
    0: "Stance",
    1: "Swing", 
    2: "None"
}

# Mapping specific modes to training categories
# Stance/Swing training will happen on these modes:
DYNAMIC_MODES = [1, 2, 3] # Level Walking, Ramp Ascent, Ramp Descent
# These modes will be forced to "None" class:
STATIC_MODES = [0, 6] # Sitting, Standing

MODE_NAMES = {
    0: "Sitting",
    1: "Level Walking",
    2: "Ramp Ascent",
    3: "Ramp Descent",
    6: "Standing"
}

def calculate_gait_phase_cycle(df):
    """
    Calculates a continuous gait phase (0.0 to 1.0) based on Heel_Strike to Heel_Strike.
    0% = Heel Strike, ~60% = Toe Off, 100% = Next Heel Strike.
    """
    if 'Heel_Strike' not in df.columns or 'Toe_Off' not in df.columns:
        return np.zeros(len(df))

    phase_cycle = np.full(len(df), np.nan)
    
    # Identify non-NaN values as events
    valid_hs = np.where(df['Heel_Strike'].notna())[0]
    
    if len(valid_hs) < 2:
        return np.zeros(len(df)) # Not enough events
    
    n_samples = len(df)
    sample_indices = np.arange(n_samples)
    
    # We can use numpy searchsorted to find the 'next' HS for each sample
    # side='right' means for sample x, we find index i such that valid_hs[i-1] <= x < valid_hs[i]
    next_hs_idx_positions = np.searchsorted(valid_hs, sample_indices, side='right')
    
    # Filter bounds: we need both previous and next HS
    # positions must be > 0 (has previous) and < len (has next)
    # However, searchsorted returns len if x > all valid_hs
    
    valid_mask = (next_hs_idx_positions > 0) & (next_hs_idx_positions < len(valid_hs))
    
    indices_to_calc = sample_indices[valid_mask]
    pos = next_hs_idx_positions[valid_mask]
    
    prev_hs = valid_hs[pos - 1]
    next_hs = valid_hs[pos]
    
    # Calculate progress
    duration = next_hs - prev_hs
    # Avoid division by zero
    duration[duration == 0] = 1 
    
    progress = (indices_to_calc - prev_hs) / duration
    
    phase_cycle[indices_to_calc] = progress
    
    # Fill NaNs. 
    # Before first HS: 0.0? Or maybe assume cycle based on first HS? Let's use 0.0
    # After last HS: 1.0? Or extrapolate? Let's use 0.0 (None state often)
    return np.nan_to_num(phase_cycle)

def extract_features_from_window(window):
    """Extract MAV, RMS, and WL features from each EMG channel."""
    features = []
    for ch in range(window.shape[1]):
        channel_data = window[:, ch]
        mav = np.mean(np.abs(channel_data))
        rms = np.sqrt(np.mean(channel_data ** 2))
        wl = np.sum(np.abs(np.diff(channel_data)))
        features.extend([mav, rms, wl])
    return np.array(features)

def load_and_preprocess_subjects(data_root, subjects, emg_channels, load_channels, target_fs):
    """Load and preprocess data from multiple subjects."""
    preprocessor = EMGPreprocessor()
    all_data = []
    
    for subject in subjects:
        print(f"\nLoading subject: {subject}")
        print("-" * 60)
        
        loader = Enabl3sDataLoader(data_root, subject, target_fs=target_fs)
        raw_dir = os.path.join(data_root, subject, 'Raw')
        if not os.path.exists(raw_dir):
            print(f"  Warning: Raw directory not found: {raw_dir}")
            continue
            
        circuit_files = [f for f in os.listdir(raw_dir) if f.endswith('_raw.csv')]
        num_circuits = len(circuit_files)
        
        circuits_to_load = range(1, num_circuits + 1)
        print(f"  Loading {num_circuits} circuits")
        
        # Load batch
        dataset_df = loader.load_dataset_batch(circuits_to_load, load_channels)
        
        if dataset_df.empty:
            print(f"  Warning: No data loaded for {subject}")
            continue

        # Filter for relevant modes
        dataset_df = dataset_df[dataset_df['Mode'].isin(DYNAMIC_MODES + STATIC_MODES)]
        
        if dataset_df.empty:
            print(f"  Warning: No valid mode data for {subject}")
            continue
        
        print(f"  Preprocessing EMG signals...")
        dataset_df[emg_channels] = preprocessor.apply_filter(dataset_df[emg_channels].values)
        dataset_df[emg_channels] = preprocessor.rectify(dataset_df[emg_channels].values)
        
        print(f"  Calculating Gait Phase Cycle...")
        # Calculate per circuit to avoid jumps
        dataset_df['Gait_Phase_Cycle'] = dataset_df.groupby('Circuit_ID', group_keys=False).apply(
            lambda x: pd.Series(calculate_gait_phase_cycle(x), index=x.index)
        )
        
        # Generate Target Class (0, 1, 2)
        # Default to None (2)
        dataset_df['Phase_Class'] = 2 
        
        # Logic for Dynamic Modes
        is_dynamic = dataset_df['Mode'].isin(DYNAMIC_MODES)
        
        # Stance (Loader=1) -> Class 0
        dataset_df.loc[is_dynamic & (dataset_df['Label_Phase'] == 1), 'Phase_Class'] = 0
        
        # Swing (Loader=0) -> Class 1
        dataset_df.loc[is_dynamic & (dataset_df['Label_Phase'] == 0), 'Phase_Class'] = 1
        
        unique_classes = sorted(dataset_df['Phase_Class'].unique())
        print(f"  Classes present: {unique_classes}")
        all_data.append(dataset_df)
    
    if not all_data:
        raise ValueError("No data loaded from any subject!")
    
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\nCombined dataset: {len(combined_df)} samples")
    return combined_df


def create_windowed_features(df, emg_channels, window_size_ms, step_size_ms, target_fs):
    """Create windowed dataset and extract features."""
    print(f"\nCreating windowed dataset...")
    
    dataset = MultiModeDataset(
        df=df,
        feature_cols=emg_channels,
        label_col='Phase_Class',
        window_size_ms=window_size_ms,
        step_size_ms=step_size_ms,
        fs=target_fs
    )
    print(f"  Total windows: {len(dataset)}")
    
    print(f"Extracting features...")
    X_windows, y_labels = [], []
    for i, (window, label) in enumerate(dataset):
        if i % 1000 == 0:
            print(f"  {i}/{len(dataset)}", end='\r')
        
        features = extract_features_from_window(window)
        X_windows.append(features)
        y_labels.append(label)
    
    print(f"  {len(dataset)}/{len(dataset)} - Done!")
    X = np.array(X_windows)
    y = np.array(y_labels)
    print(f"Feature matrix: {X.shape}, Labels: {y.shape}\n")
    return X, y


def print_class_distribution(y):
    """Print the distribution of classes in the dataset."""
    unique_labels, counts = np.unique(y, return_counts=True)
    print("Class Distribution:")
    for label, count in zip(unique_labels, counts):
        percentage = (count / len(y)) * 100
        phase_name = PHASE_NAMES.get(int(label), f"Unknown ({int(label)})")
        print(f"  {int(label)} - {phase_name:15s}: {count:6d} ({percentage:5.1f}%)")
    print()


def evaluate_and_report(model, X_test, y_test):
    """Evaluate model and print detailed metrics."""
    print("\n" + "="*60)
    print("Model Evaluation")
    print("="*60)
    
    y_pred = model.predict(X_test)
    accuracy = np.mean(y_pred == y_test)
    print(f"\nAccuracy: {accuracy * 100:.2f}%\n")
    
    unique_labels = np.unique(y_test)
    target_names = [PHASE_NAMES.get(int(label), f"Class {int(label)}") for label in unique_labels]
    
    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=target_names, zero_division=0))
    
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print()


def save_model_and_config(model, emg_channels, target_fs, window_size_ms, step_size_ms, output_dir="models"):
    """Save trained model and configuration."""
    os.makedirs(output_dir, exist_ok=True)
    
    model_path = os.path.join(output_dir, "gait_phase_classifier.pkl")
    joblib.dump(model, model_path)
    print(f"Model saved: {model_path}")
    
    config = {
        'emg_channels': emg_channels,
        'target_fs': target_fs,
        'window_size_ms': window_size_ms,
        'step_size_ms': step_size_ms,
        'feature_names': [f'{ch}_{feat}' for ch in emg_channels for feat in ['MAV', 'RMS', 'WL']],
        'phase_names': PHASE_NAMES,
        'classes': [0, 1, 2] # Stance, Swing, None
    }
    config_path = os.path.join(output_dir, "gait_phase_config.pkl")
    joblib.dump(config, config_path)
    print(f"Config saved: {config_path}")


def main():
    # Configuration
    # Ensure this runs from root
    if os.path.exists("src"):
        data_root = "data"
    else:
        # Fallback if running from src
        data_root = "../data"

    subjects = ["AB156"]
    emg_channels = ['TA', 'MG', 'RF']
    load_channels = ['TA', 'MG', 'RF', 'Mode', 'Ankle_Angle', 'Knee_Angle', 'Heel_Strike', 'Toe_Off']
    target_fs = 250
    window_size_ms = 200 
    step_size_ms = 50    
    
    print("="*60)
    print("Gait Phase Detection (Stance/Swing/None) - Training Pipeline")
    print("="*60)
    print(f"Subjects: {subjects}")
    print(f"EMG Channels: {emg_channels}")
    print(f"Sampling Rate: {target_fs} Hz")
    print(f"Window: {window_size_ms} ms, Step: {step_size_ms} ms")
    print("="*60)
    
    combined_df = load_and_preprocess_subjects(
        data_root, subjects, emg_channels, 
        load_channels, target_fs
    )
    
    X, y = create_windowed_features(
        combined_df, emg_channels, 
        window_size_ms, step_size_ms, target_fs
    )
    
    print_class_distribution(y)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {X_train.shape[0]} samples, Test: {X_test.shape[0]} samples\n")
    
    print("="*60)
    print("Training Random Forest Classifier")
    print("="*60)
    
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=20, # Increased depth slightly for better fitting
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced"
    )
    
    model.fit(X_train, y_train)
    
    evaluate_and_report(model, X_test, y_test)
    
    save_model_and_config(model, emg_channels, target_fs, window_size_ms, step_size_ms)
    
    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
