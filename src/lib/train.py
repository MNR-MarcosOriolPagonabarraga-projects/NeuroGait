import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

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