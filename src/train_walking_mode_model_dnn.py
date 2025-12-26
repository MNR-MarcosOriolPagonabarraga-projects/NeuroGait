import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow import one_hot
from .lib.data_loader import Enabl3sDataLoader
from .lib.preprocess import EMGPreprocessor
from .lib.dataset import MultiModeDataset
from .lib.train import train_tiny_dnn_model
from .lib.features import sum_channels


MODE_NAMES = {
    0: "Sitting",
    1: "Level Walking",
    2: "Ramp Ascent",
    3: "Ramp Descent",
}

def load_and_preprocess_subjects(data_root, subjects, emg_channels, load_channels, target_fs):
    """Load and preprocess data from multiple subjects."""
    preprocessor = EMGPreprocessor()
    all_data = []
    
    for subject in subjects:
        print(f"\nLoading subject: {subject}")
        print("-" * 60)
        
        loader = Enabl3sDataLoader(data_root, subject, target_fs=target_fs)
        raw_dir = os.path.join(data_root, subject, 'Raw')
        circuit_files = [f for f in os.listdir(raw_dir) if f.endswith('_raw.csv')]
        num_circuits = len(circuit_files)
        
        circuits_to_load = range(1, num_circuits + 1)
        print(f"  Loading {num_circuits} circuits")
        
        dataset_df = loader.load_dataset_batch(circuits_to_load, load_channels)
        if dataset_df.empty:
            print(f"  Warning: No data loaded, skipping...")
            continue
        
        print(f"  Preprocessing EMG signals...")
        dataset_df[emg_channels] = preprocessor.apply_filter(dataset_df[emg_channels].values)

        unique_modes = sorted(dataset_df['Mode'].unique())
        print(f"  Modes present: {unique_modes}")
        all_data.append(dataset_df)
    
    if not all_data:
        raise ValueError("No data loaded from any subject!")
    
    combined_df = pd.concat(all_data, ignore_index=True) if len(all_data) > 1 else all_data[0]
    print(f"\nCombined dataset: {len(combined_df)} samples, modes: {sorted(combined_df['Mode'].unique())}")
    return combined_df


def create_windowed_features(df, emg_channels, window_size_ms, step_size_ms, target_fs):
    """Create windowed dataset and extract features."""
    print(f"\nCreating windowed dataset...")
    dataset = MultiModeDataset(
        df=df,
        feature_cols=emg_channels,
        label_col='Mode',
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
        X_windows.append(sum_channels(window))
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
        mode_name = MODE_NAMES.get(int(label), f"Unknown ({int(label)})")
        print(f"  {int(label)} - {mode_name:15s}: {count:6d} ({percentage:5.1f}%)")
    print()


def evaluate_and_report(model, X_test, y_test):
    """Evaluate model and print detailed metrics."""
    print("\n" + "="*60)
    print("Model Evaluation")
    print("="*60)
    
    y_pred = model.predict(X_test)
    y_pred = np.argmax(y_pred, axis=1)
    y_test = np.argmax(y_test, axis=1)

    accuracy = np.mean(y_pred == y_test)
    print(f"\nAccuracy: {accuracy * 100:.2f}%\n")

    unique_labels = np.unique(y_test)
    target_names = [MODE_NAMES.get(int(label), f"Mode {int(label)}") for label in unique_labels]
    
    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=target_names, zero_division=0))
    
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print()


def save_model_and_config(model, emg_channels, target_fs, window_size_ms, step_size_ms, output_dir="models"):
    """Save trained model and configuration."""
    os.makedirs(output_dir, exist_ok=True)
    
    model_path = os.path.join(output_dir, "state_classifier.pkl")
    joblib.dump(model, model_path)
    print(f"Model saved: {model_path}")
    
    config = {
        'emg_channels': emg_channels,
        'target_fs': target_fs,
        'window_size_ms': window_size_ms,
        'step_size_ms': step_size_ms,
        'feature_names': [f'{ch}_{feat}' for ch in emg_channels for feat in ['MAV', 'RMS', 'WL']],
        'mode_names': MODE_NAMES
    }
    config_path = os.path.join(output_dir, "config.pkl")
    joblib.dump(config, config_path)
    print(f"Config saved: {config_path}")


def main():
    # Configuration
    data_root = "data"
    subjects = ["AB156"]
    emg_channels = ['TA', 'MG', 'RF']
    target_fs = 250
    window_size_ms = 2000
    step_size_ms = 100
    
    print("="*60)
    print("Multi-Mode Walking Detection - Training Pipeline")
    print("="*60)
    print(f"Subjects: {subjects}")
    print(f"EMG Channels: {emg_channels}")
    print(f"Sampling Rate: {target_fs} Hz")
    print(f"Window: {window_size_ms} ms, Step: {step_size_ms} ms")
    print("="*60)
    
    # Load and preprocess data
    combined_df = load_and_preprocess_subjects(
        data_root, subjects, emg_channels, 
        emg_channels + ['Mode'], target_fs
    )
    
    # Create features
    X, y = create_windowed_features(
        combined_df, emg_channels, 
        window_size_ms, step_size_ms, target_fs
    )
    
    # Show distribution
    print_class_distribution(y)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    y_train = one_hot(y_train, depth=len(MODE_NAMES))
    y_test = one_hot(y_test, depth=len(MODE_NAMES))
    print(f"Train: {X_train.shape[0]} samples, Test: {X_test.shape[0]} samples\n")
    
    # Train model
    print("="*60)
    print("Training State Classifier")
    print("="*60)
    input_shape = X_train.shape[1:]
    print(f"Input shape: {input_shape}")
    model = train_tiny_dnn_model(X_train, y_train, input_shape, num_output_features=len(MODE_NAMES), hidden_units=256)
    
    if model is None:
        raise RuntimeError("Model training failed!")
    
    # Evaluate
    evaluate_and_report(model, X_test, y_test)
    
    # Save
    save_model_and_config(model, emg_channels, target_fs, window_size_ms, step_size_ms)
    
    print("\n" + "="*60)
    print("Training Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
