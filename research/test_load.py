import joblib
import os
import traceback

path = 'models/v1_pyrite.pkl'
print(f"Loading {path}...")
try:
    model = joblib.load(path)
    print("✅ Success!")
    print(f"Model type: {type(model)}")
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()
