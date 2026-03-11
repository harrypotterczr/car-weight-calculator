import sys
import json
import joblib
import numpy as np
import os

def predict_weight(model_path, parameters, param_order=None):
    model = joblib.load(model_path)
    
    if hasattr(model, 'feature_names_in_'):
        feature_names = model.feature_names_in_
    elif param_order:
        feature_names = param_order
    else:
        raise ValueError("Model has no feature_names_in_ attribute and no param_order provided")
    
    features = []
    for feature in feature_names:
        if feature in parameters:
            features.append(float(parameters[feature]))
        else:
            raise ValueError(f"Missing parameter: {feature}")
    
    X = np.array(features).reshape(1, -1)
    
    prediction = model.predict(X)
    
    return float(prediction[0])

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python predict_rf.py <model_path> <parameters_json> [param_order_json]")
        sys.exit(1)
    
    model_path = sys.argv[1]
    parameters_json = sys.argv[2]
    param_order = None
    
    if len(sys.argv) >= 4:
        try:
            param_order = json.loads(sys.argv[3])
        except:
            pass
    
    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}")
        sys.exit(1)
    
    try:
        parameters = json.loads(parameters_json)
        result = predict_weight(model_path, parameters, param_order)
        print(result)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
