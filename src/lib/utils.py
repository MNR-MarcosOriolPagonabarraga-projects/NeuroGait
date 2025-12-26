import numpy as np
from sklearn.tree import _tree

def export_dt_to_cpp(tree, file, func_name="predict_tree"):
    """Recursive function to write C++ if-else tree code."""
    tree_ = tree.tree_
    feature_name = [
        f"features[{i}]" if i != _tree.TREE_UNDEFINED else "undefined!"
        for i in tree_.feature
    ]
    
    def recurse(node, depth):
        indent = "  " * depth
        if tree_.feature[node] != _tree.TREE_UNDEFINED:
            name = feature_name[node]
            threshold = tree_.threshold[node]
            file.write(f"{indent}if ({name} <= {threshold:.6f}) {{\n")
            recurse(tree_.children_left[node], depth + 1)
            file.write(f"{indent}}} else {{\n")
            recurse(tree_.children_right[node], depth + 1)
            file.write(f"{indent}}}\n")
        else:
            class_idx = np.argmax(tree_.value[node][0])
            file.write(f"{indent}return {class_idx};\n")

    file.write(f"int {func_name}(const double* features) {{\n")
    recurse(0, 1)
    file.write("}\n\n")

def export_lda_to_cpp(model, file, prefix="LDA"):
    """Exports LDA model to C++ constants and predict function."""
    weights = model.coef_[0]
    bias = model.intercept_[0]
    n_features = len(weights)
    
    file.write(f"// {prefix} Model (LDA)\n")
    file.write(f"const int {prefix}_N_FEATURES = {n_features};\n")
    file.write(f"const double {prefix}_WEIGHTS[{prefix}_N_FEATURES] = {{")
    file.write(", ".join([f"{w:.6f}" for w in weights]))
    file.write("};\n")
    file.write(f"const double {prefix}_BIAS = {bias:.6f};\n\n")
    
    file.write(f"int predict_{prefix.lower()}(const double* features) {{\n")
    file.write(f"    double score = {prefix}_BIAS;\n")
    file.write(f"    for(int i=0; i<{prefix}_N_FEATURES; i++) score += features[i] * {prefix}_WEIGHTS[i];\n")
    file.write(f"    return (score > 0) ? 1 : 0;\n")
    file.write("}\n\n")

def export_rf_to_cpp(model, file, prefix="RF"):
    """Exports Random Forest to C++."""
    # Export individual trees
    for i, estimator in enumerate(model.estimators_):
        export_dt_to_cpp(estimator, file, f"{prefix.lower()}_tree_{i}")
    
    # Voting logic
    n_trees = len(model.estimators_)
    file.write(f"int predict_{prefix.lower()}(const double* features) {{\n")
    file.write(f"    int votes[{model.n_classes_}] = {{0}};\n") # Assumes classes 0..N
    file.write("    int prediction;\n")
    for i in range(n_trees):
        file.write(f"    prediction = {prefix.lower()}_tree_{i}(features);\n")
        file.write(f"    votes[prediction]++;\n")
    
    # Argmax
    file.write("    int max_votes = -1;\n")
    file.write("    int best_class = 0;\n")
    file.write(f"    for(int i=0; i<{model.n_classes_}; i++) {{\n")
    file.write("        if(votes[i] > max_votes) { max_votes = votes[i]; best_class = i; }\n")
    file.write("    }\n")
    file.write("    return best_class;\n")
    file.write("}\n\n")

def generate_cpp_header(models, system_name="Hierarchical", filename="embedded/classifier.h"):
    """
    Generates C++ header for one or more models.
    
    Args:
        models: Dictionary { 'State': model1, 'Phase': model2 } OR single model.
        system_name: Name of the system.
        filename: Output path.
    """
    print(f"Exporting {system_name} system to {filename}...")
    
    # Backward compatibility: if models is not dict, wrap it
    if not isinstance(models, dict):
        # We don't know the name, assume "Model"
        models = {"Model": models}
        
    with open(filename, "w") as f:
        f.write(f"#ifndef {system_name.upper()}_CLASSIFIER_H\n")
        f.write(f"#define {system_name.upper()}_CLASSIFIER_H\n\n")
        f.write("#include <cmath>\n\n")
        
        # Export each model
        for name, model in models.items():
            model_type = type(model).__name__
            print(f"  Exporting {name} ({model_type})...")
            
            if "LinearDiscriminantAnalysis" in model_type:
                export_lda_to_cpp(model, f, prefix=name.upper())
            elif "RandomForest" in model_type:
                export_rf_to_cpp(model, f, prefix=name.upper())
            elif "DecisionTree" in model_type:
                export_dt_to_cpp(model, f, f"predict_{name.lower()}")
            else:
                 print(f"Error: Unknown model type {model_type} for {name}")
        
        # System Logic
        if system_name == "Hierarchical":
             f.write("// Hierarchical Control Logic\n")
             f.write("// State Modes: 0=Sitting, 1=Level Walking, 3=Ramp, 4=Terrain, 6=Standing\n")
             f.write("int predict_hierarchical(const double* features) {\n")
             f.write("    // Layer 1: Identify Global State\n")
             f.write("    int state = predict_state(features);\n\n")
             f.write("    // Layer 2: Dispatch to Phase Estimator (only for Walking)\n")
             f.write("    if (state == 1) {  // Level Walking\n")
             f.write("        // Return gait phase: 0=Stance, 1=Swing\n")
             f.write("        return predict_phase(features);\n")
             f.write("    } else {\n")
             f.write("        // For static states (Sitting/Standing) or non-level terrain,\n")
             f.write("        // return Stance (0) as default safe state\n")
             f.write("        return 0;\n")
             f.write("    }\n")
             f.write("}\n\n")
             f.write("// Helper function: Get current state name\n")
             f.write("const char* get_state_name(int state) {\n")
             f.write("    switch(state) {\n")
             f.write("        case 0: return \"Sitting\";\n")
             f.write("        case 1: return \"Walking\";\n")
             f.write("        case 3: return \"Ramp\";\n")
             f.write("        case 4: return \"Terrain\";\n")
             f.write("        case 6: return \"Standing\";\n")
             f.write("        default: return \"Unknown\";\n")
             f.write("    }\n")
             f.write("}\n")


        f.write(f"#endif // {system_name.upper()}_CLASSIFIER_H\n")


def resample_df(df, target_fs, column_name):
    """Resample DataFrame to target sampling frequency."""
    period_us = int(1_000_000 / target_fs)
    df = df.resample(f'{period_us}us').mean()
    df[column_name] = df[column_name].resample(f'{period_us}us').median().round()
    
    return df