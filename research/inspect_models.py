import joblib
import os
import sys
import pandas as pd

# Path setup
BASE_DIR = os.getcwd()
sys.path.append(os.path.join(BASE_DIR, 'src'))

def inspect_models():
    model_files = [
        'v1_pyrite.pkl', 'v2_diamond.pkl', 'v3_obsidian.pkl', 
        'v4_quartz.pkl', 'v5_conformal_sniper.json'
    ]
    
    for mf in model_files:
        path = os.path.join('models', mf)
        print(f"\n--- {mf} ---")
        if not os.path.exists(path):
            print("❌ File not found")
            continue
            
        try:
            if mf.endswith('.pkl'):
                model = joblib.load(path)
                if hasattr(model, 'feature_names_in_'):
                    print(f"Features: {list(model.feature_names_in_)}")
                elif hasattr(model, 'get_booster'):
                    print(f"Features (Booster): {model.get_booster().feature_names}")
                else:
                    print("Could not determine feature names (no feature_names_in_ or get_booster)")
            elif mf.endswith('.json'):
                print("JSON model (XGBoost/LightGBM). Cannot easily inspect features without loading into booster.")
                # We can try to load it
                import xgboost as xgb
                booster = xgb.Booster()
                booster.load_model(path)
                print(f"Features: {booster.feature_names}")
        except Exception as e:
            print(f"❌ Error inspecting {mf}: {e}")

if __name__ == "__main__":
    inspect_models()
