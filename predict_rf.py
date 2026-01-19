import sys
import json
import joblib
import numpy as np
import os

def predict_weight(model_path, parameters):
    # 加载模型
    model = joblib.load(model_path)
    
    # 获取特征名称
    feature_names = model.feature_names_in_
    
    # 创建特征数组
    features = []
    for feature in feature_names:
        if feature in parameters:
            features.append(float(parameters[feature]))
        else:
            raise ValueError(f"Missing parameter: {feature}")
    
    # 转换为numpy数组并重塑
    X = np.array(features).reshape(1, -1)
    
    # 进行预测
    prediction = model.predict(X)
    
    return float(prediction[0])

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python predict_rf.py <model_path> <parameters_json>")
        sys.exit(1)
    
    model_path = sys.argv[1]
    parameters_json = sys.argv[2]
    
    # 检查模型文件是否存在
    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}")
        sys.exit(1)
    
    try:
        parameters = json.loads(parameters_json)
        result = predict_weight(model_path, parameters)
        print(result)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)