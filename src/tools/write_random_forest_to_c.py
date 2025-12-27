import sys
import joblib
import numpy as np

FLOAT_TYPE = "float" 

def load_model(path):
    with open(path, 'rb') as f:
        return joblib.load(f)

def generate_tree_code(tree, tree_index):
    """
    Generates a C++ function for a single decision tree.
    """
    feature = tree.feature
    threshold = tree.threshold
    children_left = tree.children_left
    children_right = tree.children_right
    value = tree.value

    # We use a list to build strings efficiently
    code = []
    
    # Define the function for this specific tree
    code.append(f"{FLOAT_TYPE} tree_{tree_index}({FLOAT_TYPE}* sample) {{")

    def recurse(node, depth):
        indent = "    " * (depth + 1)
        
        # Check if this is a leaf node
        if children_left[node] == children_right[node]:
            # LEAF NODE
            # value[node] is an array. 
            # For Regression: it's [[prediction]]
            # For Classification: it's [[count_class0, count_class1...]]
            
            # We assume a simple single-value output (Regression or Binary Prob)
            # If you have multi-class, you might need to return a class index here.
            
            # Get the scalar value. 
            # Note: For classifiers, sklearn trees store *counts*. 
            # We usually normalize later, but for this script, we return the 
            # dominant value or weight.
            val = value[node][0]
            if isinstance(val, np.ndarray):
                # Handle cases where value is multidimensional
                 # For Random Forest Regressor, it's just val[0]
                 # For Classifier, we typically return the probability of class 1
                 # But to keep C++ simple, let's return the raw value of the 1st output
                 leaf_val = val[0] 
            else:
                leaf_val = val
            
            code.append(f"{indent}return {leaf_val};")
        else:
            # DECISION NODE
            feat_idx = feature[node]
            thres = threshold[node]
            
            code.append(f"{indent}if (sample[{feat_idx}] <= {thres}) {{")
            recurse(children_left[node], depth + 1)
            code.append(f"{indent}}} else {{")
            recurse(children_right[node], depth + 1)
            code.append(f"{indent}}}")

    # Start recursion from root (node 0)
    recurse(0, 0)
    
    code.append("}\n")
    return "\n".join(code)

def generate_forest_code(model):
    """
    Generates the main C++ file with all tree functions and a wrapper.
    """
    code_segments = []
    
    # 1. Add Headers
    code_segments.append("#include <iostream>")
    code_segments.append("#include <vector>")
    code_segments.append("")

    # 2. Generate function for each tree
    # Check if model is a list (some custom wrappers) or standard sklearn object
    if hasattr(model, 'estimators_'):
        estimators = model.estimators_
    else:
        print("Error: Could not find 'estimators_'. Is this a standard sklearn RandomForest?")
        return

    print(f"Converting {len(estimators)} trees...")
    
    for i, estimator in enumerate(estimators):
        # The underlying DecisionTree object is in estimator.tree_
        tree_code = generate_tree_code(estimator.tree_, i)
        code_segments.append(tree_code)
    
    code_segments.append(f"// Main prediction function")
    code_segments.append(f"{FLOAT_TYPE} predict_forest({FLOAT_TYPE}* features) {{")
    code_segments.append(f"    {FLOAT_TYPE} sum = 0.0;")
    
    for i in range(len(estimators)):
        code_segments.append(f"    sum += tree_{i}(features);")
    
    n_trees = len(estimators)
    
    code_segments.append(f"    return sum / {n_trees}.0;")
    code_segments.append("}")

    return "\n".join(code_segments)

if __name__ == "__main__":
    MODEL_PATH = sys.argv[1]
    OUTPUT_FILE = sys.argv[2]
    print(f"Loading {MODEL_PATH}...")
    try:
        model = load_model(MODEL_PATH)
        c_code = generate_forest_code(model)
        
        if c_code:
            with open(OUTPUT_FILE, "w") as f:
                f.write(c_code)
            print(f"Success! Model written to {OUTPUT_FILE}")
            print(f"Generated C++ size: {len(c_code)/1024:.2f} KB")
    except Exception as e:
        print(f"An error occurred: {e}")