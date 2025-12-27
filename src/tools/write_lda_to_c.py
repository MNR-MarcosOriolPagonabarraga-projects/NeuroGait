import sys
import joblib
import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis


FLOAT_TYPE = "float"
FUNC_NAME = "predict_lda"


def generate_lda_cpp(model_path, output_path):
    print(f"Loading LDA model from {model_path}...")
    try:
        clf = joblib.load(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    if not hasattr(clf, 'coef_') or not hasattr(clf, 'intercept_'):
        print("Error: El modelo no tiene los atributos 'coef_' o 'intercept_'. Asegúrate de que está entrenado.")
        sys.exit(1)

    coef = clf.coef_
    intercept = clf.intercept_
    classes = clf.classes_
    
    n_rows, n_features = coef.shape
    
    cpp_code = []
    cpp_code.append(f"// Generated C++ code for Linear Discriminant Analysis")
    cpp_code.append(f"// Source Model: {model_path}")
    cpp_code.append("#include <vector>")
    cpp_code.append("")

    if n_rows == 1:
        print("Detected Binary Classification.")
        
        bias = intercept[0]
        weights = coef[0]
        
        cpp_code.append(f"const int LDA_N_FEATURES = {n_features};")
        cpp_code.append(f"const {FLOAT_TYPE} LDA_INTERCEPT = {bias:.8f};")
        
        weights_str = ", ".join([f"{w:.8f}" for w in weights])
        cpp_code.append(f"const {FLOAT_TYPE} LDA_WEIGHTS[{n_features}] = {{ {weights_str} }};")
        cpp_code.append("")
        
        cpp_code.append(f"// Returns class {classes[1]} if score > 0, else {classes[0]}")
        cpp_code.append(f"int {FUNC_NAME}({FLOAT_TYPE}* input_data) {{")
        cpp_code.append(f"    {FLOAT_TYPE} score = LDA_INTERCEPT;")
        cpp_code.append(f"    for (int i = 0; i < LDA_N_FEATURES; ++i) {{")
        cpp_code.append(f"        score += input_data[i] * LDA_WEIGHTS[i];")
        cpp_code.append(f"    }}")
        cpp_code.append(f"    return (score > 0) ? {classes[1]} : {classes[0]};")
        cpp_code.append(f"}}")

    else:
        print(f"Detected Multiclass Classification ({n_rows} classes).")
        n_classes = n_rows
        
        intercepts_str = ", ".join([f"{b:.8f}" for b in intercept])
        cpp_code.append(f"const {FLOAT_TYPE} LDA_INTERCEPTS[{n_classes}] = {{ {intercepts_str} }};")
        
        all_weights = coef.flatten()
        weights_str = ", ".join([f"{w:.8f}" for w in all_weights])
        cpp_code.append(f"const {FLOAT_TYPE} LDA_WEIGHTS[{n_classes * n_features}] = {{ {weights_str} }};")
        cpp_code.append(f"const int LDA_CLASSES[{n_classes}] = {{ " + ", ".join(map(str, classes)) + " };")
        cpp_code.append("")
        
        cpp_code.append(f"int {FUNC_NAME}({FLOAT_TYPE}* input_data) {{")
        cpp_code.append(f"    int best_idx = 0;")
        cpp_code.append(f"    {FLOAT_TYPE} max_score = -1e9;")
        cpp_code.append(f"")
        cpp_code.append(f"    for (int c = 0; c < {n_classes}; ++c) {{")
        cpp_code.append(f"        {FLOAT_TYPE} current_score = LDA_INTERCEPTS[c];")
        cpp_code.append(f"        for (int i = 0; i < {n_features}; ++i) {{")
        cpp_code.append(f"            current_score += input_data[i] * LDA_WEIGHTS[c * {n_features} + i];")
        cpp_code.append(f"        }}")
        cpp_code.append(f"        if (current_score > max_score) {{")
        cpp_code.append(f"            max_score = current_score;")
        cpp_code.append(f"            best_idx = c;")
        cpp_code.append(f"        }}")
        cpp_code.append(f"    }}")
        cpp_code.append(f"    return LDA_CLASSES[best_idx];")
        cpp_code.append(f"}}")

    try:
        with open(output_path, "w") as f:
            f.write("\n".join(cpp_code))
        print(f"Success! C++ code written to {output_path}")
    except Exception as e:
        print(f"Error writing to file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python write_lda_to_c.py <model_pkl_path> <output_cpp_path>")
    else:
        generate_lda_cpp(sys.argv[1], sys.argv[2])