import os
import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.tree import DecisionTreeClassifier, _tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from .data_loader import Enabl3sDataLoader
from .preprocessing import EMGPreprocessor
from .utils import generate_cpp_header

def main():
    data_root = "data"
    subjects = [d for d in os.listdir(data_root)]
    subjects.sort()
    
    print(f"Found {len(subjects)} subjects: {subjects}")
    
    preprocessor = EMGPreprocessor()
    channels = ['TA', 'MG', 'RF', 'Ankle_Angle']
    
    all_X = []
    all_y = []
    
    for subject in subjects:
        try:
            loader = Enabl3sDataLoader(data_root, subject)
            circuits_path = os.path.join(data_root, subject, 'Raw')
            subject_circuits = os.listdir(circuits_path)

            for cid in range(1, len(subject_circuits) + 1):
                df = loader.load_circuit(cid, channels)
                if df.empty or 'Ankle_Angle' not in df.columns: continue

                threshold = 0.0 
                df = loader.add_gait_phase_label(df, 'Ankle_Angle', threshold=threshold)
                
                raw = df[['TA', 'MG', 'RF']].values
                filt = preprocessor.apply_filter(raw)
                rect = preprocessor.rectify(filt)
                feats = preprocessor.compute_features(rect)
                
                n_wins = feats.shape[0]
                labels = []
                for i in range(n_wins):
                    target_idx = (i * 20) + 10 + 20 
                    
                    if target_idx < len(df): 
                        labels.append(df['Label_Phase'].iloc[target_idx])
                    else: 
                        labels.append(0)
                        
                all_X.append(feats)
                all_y.append(np.array(labels))
                
        except Exception as e:
            print(f"Skipping {subject}: {e}")

    if not all_X: return

    print("\nConcatenating datasets...")
    X = np.vstack(all_X)
    y = np.concatenate(all_y)
    
    # Splits
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Training Samples: {X_train.shape[0]}, Test Samples: {X_test.shape[0]}")
    
    # Model Comparison
    models = {
        "LDA": LinearDiscriminantAnalysis(),
        "DecisionTree": DecisionTreeClassifier(max_depth=10, min_samples_leaf=10),
        "RandomForest": RandomForestClassifier(n_estimators=10, max_depth=8, min_samples_leaf=10, n_jobs=-1),
        "MLP": MLPClassifier(hidden_layer_sizes=(16,), max_iter=200, activation='relu')
    }
    
    best_acc = 0
    best_model = None
    best_name = ""
    
    print("\n--- Model Benchmark ---")
    for name, clf in models.items():
        print(f"Training {name}...")
        clf.fit(X_train, y_train)
        acc = clf.score(X_test, y_test)
        print(f"  Accuracy: {acc*100:.2f}%")
        
        if acc > best_acc:
            best_acc = acc
            best_model = clf
            best_name = name
            
    print(f"\nWinner: {best_name} with {best_acc*100:.2f}%")
        
    generate_cpp_header(best_model, best_name, 'embedded/classifier.h')

if __name__ == "__main__":
    main()
