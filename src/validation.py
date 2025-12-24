import pandas as pd
import numpy as np
import os
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.metrics import accuracy_score, classification_report
import joblib # If we were saving the model object, but we are just re-running simplified validation here or we should save it.
# To properly validate, we should modify train_model to SAVE the model to a .pkl, 
# or Validation should Re-Train then Test (Pipeline validation).
# For simplicity in this mono-script, I will just implement a full pipeline test function that can be imported 
# OR I will rely on train_model.py doing a split? 
# The README says "Simulation: Test the full pipeline on a 'held-out' circuit".
# So I'll implement a standalone validation script that trains (or loads if I saved it) and tests.
# I will make Validation script IMPORT train_model functions if I refactor, 
# but currently train_model is a script.
# Actually, the best way for now: Copy-paste the Logic or make train_model reusable.
# I'll make train_model reusable by extracting a `train_pipeline` function.
# But for now, to avoid rewriting train_model, I'll just re-implement the pipeline in validation 
# which acts as the "Simulation" step.

# Actually, I'll update train_model.py to save the model using pickle so Validation can load it.
# Wait, I already wrote train_model.py. I can stick to "Retrain" or "Load weights".
# Loading weights into sklearn LDA manually is hard.
# I will just do a Train-Test split inside train_model.py to show performance, 
# AND/OR validation.py will load a NEW circuit and run the specific metric checks.

# Use re-usable components.
from data_loader import Enabl3sDataLoader
from preprocessing import EMGPreprocessor

# Hack: Re-train for validation to ensure environment consistency, 
# or assuming the user runs train first then validation?
# The prompt asks to "Implement validation.py".
# I'll implement a class `NeuroGaitPipeline` in a new file or just duplicte logic for speed?
# Duplication is messy but fast. Refactoring is better.
# I will Refactor `train_model.py` to `pipeline.py`? 
# No, I'll just import the necessary classes and in validation.py I will Training on 1-10 and Test on 11.
# It simulates the workflow.

def evaluate_circuit(circuit_id, train_circuit_range=(1, 5)):
    # 1. Train (Quickly re-train or ideally load model)
    # For this task, I will do a quick Retrain on a smaller set to get the model object,
    # unless I update train_model to save it.
    # Let's assume validation.py is the "Test on held-out" script.
    
    print(f"--- Validating on Circuit {circuit_id} ---")
    
    # LOAD DATA
    data_root = "data/AB156"
    loader = Enabl3sDataLoader(os.path.dirname(data_root), "AB156")
    preprocessor = EMGPreprocessor()
    
    # TRAIN (Setup Reference Model)
    # Using circuits 1-3 for speed in validation test, or full range 1-10
    # TRAIN (Setup Reference Model)
    # Using circuits 1-5 for speed in validation test, or full range 1-10
    print("Training Reference Model (Circuits 1-5)...")
    channels = ['TA', 'MG', 'RF', 'Ankle_Angle']
    df_train = loader.load_dataset_batch(range(train_circuit_range[0], train_circuit_range[1] + 1), channels)
    threshold = 0.0 # Ignored by robust loader
    df_train = loader.add_gait_phase_label(df_train, 'Ankle_Angle', threshold=threshold)
    
    raw_train = df_train[['TA', 'MG', 'RF']].values
    filt_train = preprocessor.apply_filter(raw_train)
    rect_train = preprocessor.rectify(filt_train)
    X_train = preprocessor.compute_features(rect_train)
    
    # Subsample Labels
    window_samples = 100 # ms
    step_samples = 100 # ms
    y_train = []
    # Simplified label extraction for speed (should match train_model logic)
    # We really should have shared logic. 
    # But I'll stick to this pattern for now.
    
    n_wins = X_train.shape[0]
    # Re-calculate indices logic to be exact?
    # X_train comes from raw_train size.
    # preprocessor.compute_features handles loops.
    # We need to match Y.
    # compute_features returns N windows.
    # We need N labels.
    
    # Let's encapsulate Label extraction to be safe.
    def get_labels(df, n_windows, step_sz=100, win_sz=100):
        lbls = []
        for i in range(n_windows):
            # Center: (i * step) + (win // 2)
            # Lookahead: + 100 samples (100ms) to reduce latency
            target_idx = (i * step_sz) + (win_sz // 2) + 100
            
            if target_idx < len(df):
                lbls.append(df['Label_Phase'].iloc[target_idx])
            else:
                lbls.append(0) 
        return np.array(lbls)

    y_train = get_labels(df_train, X_train.shape[0])
    
    lda = LinearDiscriminantAnalysis()
    lda.fit(X_train, y_train)
    
    # TEST
    print(f"Testing on Circuit {circuit_id}...")
    df_test = loader.load_circuit(circuit_id, channels)
    if df_test.empty:
        print("Test circuit empty.")
        return

    df_test = loader.add_gait_phase_label(df_test, 'Ankle_Angle', threshold=threshold)
    
    raw_test = df_test[['TA', 'MG', 'RF']].values
    filt_test = preprocessor.apply_filter(raw_test)
    rect_test = preprocessor.rectify(filt_test)
    X_test = preprocessor.compute_features(rect_test)
    y_test = get_labels(df_test, X_test.shape[0])
    
    # Predict
    y_pred = lda.predict(X_test)
    
    # Metrics
    acc = accuracy_score(y_test, y_pred)
    print(f"Validation Accuracy: {acc*100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Stance', 'Swing']))
    
    # Time to Trigger Analysis
    gt_onsets = np.where(np.diff(y_test) == 1)[0]
    pred_onsets = np.where(np.diff(y_pred) == 1)[0]
    
    delays = []
    
    for onset in gt_onsets:
        future_preds = pred_onsets[pred_onsets >= onset]
        if len(future_preds) > 0:
            first_pred = future_preds[0]
            if first_pred - onset < 10: 
                delay_samples = first_pred - onset
                delay_ms = delay_samples * 100.0
                delays.append(delay_ms)
    
    if delays:
        avg_delay = np.mean(delays)
        print(f"\nAverage Time to Trigger: {avg_delay:.2f} ms")
        if avg_delay <= 100:
            print("SUCCESS: Latency within 100ms requirement.")
        else:
            print("WARNING: Latency exceeds 100ms requirement.")
    else:
        print("\nNo Swing Phases detected or matched.")

if __name__ == "__main__":
    evaluate_circuit(11)
