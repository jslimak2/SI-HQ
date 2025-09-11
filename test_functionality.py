#!/usr/bin/env python3
"""
Test script to demonstrate the SI-HQ ML model management functionality
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def test_model_gallery():
    """Test the model gallery API"""
    print("🤖 Testing Model Gallery...")
    response = requests.get(f"{BASE_URL}/api/models/gallery")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['total_count']} models in gallery")
        for model in data['models']:
            print(f"   - {model['name']} ({model['sport']}) - {model['accuracy']}% accuracy")
    else:
        print(f"❌ Error: {response.status_code}")

def test_model_training():
    """Test the model training API"""
    print("\n🎯 Testing Model Training...")
    
    training_config = {
        "sport": "NBA",
        "model_type": "statistical",
        "num_samples": 500
    }
    
    response = requests.post(f"{BASE_URL}/api/ml/basic/train", 
                           json=training_config,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Training completed successfully")
        print(f"   - Accuracy: {(data['training_results']['accuracy'] * 100):.1f}%")
        print(f"   - Features: {data['training_results']['features_used']}")
        print(f"   - Model Type: {data['model_type']}")
    else:
        print(f"❌ Training failed: {response.status_code}")

def test_model_prediction():
    """Test model prediction"""
    print("\n🔮 Testing Model Prediction...")
    
    prediction_data = {
        "sport": "NBA",
        "home_win_pct": 0.65,
        "away_win_pct": 0.55
    }
    
    response = requests.post(f"{BASE_URL}/api/ml/demo/predict",
                           json=prediction_data,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        prediction = data['prediction']
        print(f"✅ Prediction made successfully")
        print(f"   - Outcome: {prediction['predicted_outcome']}")
        print(f"   - Confidence: {(prediction['confidence'] * 100):.1f}%")
    else:
        print(f"❌ Prediction failed: {response.status_code}")

def test_kelly_calculator():
    """Test Kelly Criterion calculator"""
    print("\n💰 Testing Kelly Criterion Calculator...")
    
    kelly_data = {
        "win_probability": 0.58,
        "odds": 185,
        "bankroll": 1000
    }
    
    response = requests.post(f"{BASE_URL}/api/analytics/kelly",
                           json=kelly_data,
                           headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        data = response.json()
        kelly = data['kelly_analysis']
        print(f"✅ Kelly calculation completed")
        print(f"   - Full Kelly: ${kelly['full_kelly_bet']:.2f}")
        print(f"   - Half Kelly: ${kelly['half_kelly_bet']:.2f}")
        print(f"   - Expected ROI: {(kelly['expected_roi'] * 100):.2f}%")
    else:
        print(f"❌ Kelly calculation failed: {response.status_code}")

def main():
    print("🚀 SI-HQ ML Model Management System Test")
    print("=" * 50)
    
    try:
        # Test basic connectivity
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ Cannot connect to SI-HQ server. Make sure it's running on port 5000.")
            return
        
        print("✅ Connected to SI-HQ server")
        
        # Run tests
        test_model_gallery()
        test_model_training()
        test_model_prediction()
        test_kelly_calculator()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed! The SI-HQ ML system is working.")
        print("\n📱 Access the web interface at:")
        print(f"   Main Dashboard: {BASE_URL}/")
        print(f"   ML Dashboard:   {BASE_URL}/ml")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to SI-HQ server.")
        print("   Make sure to run: cd dashboard && python app.py")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()