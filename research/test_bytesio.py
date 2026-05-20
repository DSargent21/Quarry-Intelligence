import joblib
import io
import os
import traceback

path = 'models/v1_pyrite.pkl'
print(f"Loading {path} via BytesIO...")
try:
    with open(path, 'rb') as f:
        data = f.read()
    model = joblib.load(io.BytesIO(data))
    print("✅ Success!")
    print(f"Model type: {type(model)}")
except Exception as e:
    print(f"❌ Failed: {e}")
    traceback.print_exc()
