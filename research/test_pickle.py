import pickle
import os
import traceback

path = 'models/v1_pyrite.pkl'
print(f"Loading {path} with pickle...")
try:
    with open(path, 'rb') as f:
        model = pickle.load(f, encoding='latin1')
    print("✅ Success with latin1!")
    print(f"Model type: {type(model)}")
except Exception as e:
    print(f"❌ Failed with latin1: {e}")
    traceback.print_exc()
