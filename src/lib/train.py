import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from tensorflow import keras
from tensorflow.keras import layers

def train_state_classifier(X, y):
    """
    Layer 1: Global State Classifier.
    Target: 0 (Sit), 6 (Stand), 1 (Walk), 2 (Ramp), etc.
    """
    print(f"\nTraining Layer 1 (State Classifier) on {len(np.unique(y))} modes: {np.unique(y)}")
    
    if len(np.unique(y)) < 2:
        print("Warning: Only 1 mode found. State Classifier will be trivial.")
        return None

    clf = RandomForestClassifier(n_estimators=20, max_depth=10, min_samples_leaf=10, n_jobs=-1, random_state=42)
    clf.fit(X, y)
    return clf

def train_phase_classifier(X, y):
    """
    Layer 2: Gait Phase Estimator (One valid mode: Walking).
    Target: 0 (Stance), 1 (Swing).
    """
    print(f"\nTraining Layer 2 (Phase Classifier) on {len(y)} samples.")
    
    clf = LinearDiscriminantAnalysis()
    clf.fit(X, y)
    return clf

def train_tiny_dnn_model(X, y, input_shape, num_output_features=6, hidden_units=16):
    # Create model
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.Flatten(),
        layers.Dense(hidden_units, activation='relu', name='hidden1'),
        layers.Dense(hidden_units // 2, activation='relu', name='hidden2'),
        layers.Dense(num_output_features, activation='linear', name='output')
    ], name='TinyDNN_EMG_FeatureExtractor')
    
    # Compile with a simple loss (will be updated during actual training)
    model.compile(
        optimizer='adam',
        loss='mse',
        metrics=['mae']
    )

    model.fit(X, y, epochs=10, batch_size=32, verbose=1)
    
    return model