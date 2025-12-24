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

def generate_cpp_header(model, model_type, filename="embedded/classifier.h"):
    print(f"Exporting {model_type} to C++...")
    
    with open(filename, "w") as f:
        f.write("#ifndef CLASSIFIER_H\n")
        f.write("#define CLASSIFIER_H\n\n")
        f.write("#include <cmath>\n\n")
        
        if model_type == "LDA":
            weights = model.coef_[0]
            bias = model.intercept_[0]
            f.write(f"const int N_FEATURES = {len(weights)};\n")
            f.write("const double LDA_WEIGHTS[N_FEATURES] = {")
            f.write(", ".join([f"{w:.6f}" for w in weights]))
            f.write("};\n")
            f.write(f"const double LDA_BIAS = {bias:.6f};\n\n")
            f.write("int predict(const double* features) {\n")
            f.write("    double score = LDA_BIAS;\n")
            f.write("    for(int i=0; i<N_FEATURES; i++) score += features[i] * LDA_WEIGHTS[i];\n")
            f.write("    return (score > 0) ? 1 : 0;\n")
            f.write("}\n")
            
        elif model_type == "DecisionTree":
            export_dt_to_cpp(model, f, "predict")
            
        elif model_type == "RandomForest":
            # Export individual trees
            for i, estimator in enumerate(model.estimators_):
                export_dt_to_cpp(estimator, f, f"predict_tree_{i}")
            
            # Voting logic
            f.write("int predict(const double* features) {\n")
            f.write("    int votes = 0;\n")
            for i in range(len(model.estimators_)):
                f.write(f"    votes += predict_tree_{i}(features);\n")
            f.write(f"    return (votes > {len(model.estimators_)//2}) ? 1 : 0;\n")
            f.write("}\n")
            
        elif "MLP" in model_type: 
            weights_input = model.coefs_[0]
            bias_input = model.intercepts_[0]
            weights_output = model.coefs_[1]
            bias_output = model.intercepts_[1]
            
            n_in = weights_input.shape[0]
            n_hidden = weights_input.shape[1]
            n_out = weights_output.shape[1]
            
            f.write(f"const int N_IN = {n_in};\n")
            f.write(f"const int N_HIDDEN = {n_hidden};\n")
            
            f.write("const double W1[N_IN][N_HIDDEN] = {\n")
            for row in weights_input:
                f.write("  {" + ", ".join([f"{w:.6f}" for w in row]) + "},\n")
            f.write("};\n\n")
            
            f.write("const double B1[N_HIDDEN] = {")
            f.write(", ".join([f"{b:.6f}" for b in bias_input]))
            f.write("};\n\n")
            
            f.write("const double W2[N_HIDDEN] = {")
            f.write(", ".join([f"{w[0]:.6f}" for w in weights_output]))
            f.write("};\n\n")
            
            f.write(f"const double B2 = {bias_output[0]:.6f};\n\n")
            
            f.write("double relu(double x) { return x > 0 ? x : 0; }\n\n")
            
            f.write("int predict(const double* features) {\n")
            f.write("    double hidden[N_HIDDEN];\n")
            f.write("    for(int i=0; i<N_HIDDEN; i++) {\n")
            f.write("        hidden[i] = B1[i];\n")
            f.write("        for(int j=0; j<N_IN; j++) hidden[i] += features[j] * W1[j][i];\n")
            f.write("        hidden[i] = relu(hidden[i]);\n")
            f.write("    }\n")
            f.write("    double score = B2;\n")
            f.write("    for(int i=0; i<N_HIDDEN; i++) score += hidden[i] * W2[i];\n")
            f.write("    return (score > 0) ? 1 : 0;\n")
            f.write("}\n")

        f.write("#endif // CLASSIFIER_H\n")