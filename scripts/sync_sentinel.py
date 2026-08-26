import os
import json
import requests
import hashlib
from datetime import datetime

def run_diagnostics():
    print("\n" + "!"*60)
    print("🚀 QUARRY // INSTITUTIONAL SYNC SENTINEL")
    print("!"*60)
    
    BASE_URL = "https://dsargent21.github.io/Quarry-Intelligence"
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_stats_path = os.path.join(base_dir, 'docs', 'web', 'stats.json')
    
    # 1. Local State
    if not os.path.exists(local_stats_path):
        print("❌ CRITICAL: Local stats.json missing from docs/web/")
        return

    with open(local_stats_path, 'r') as f:
        local_data = json.load(f)
        local_update = local_data.get('meta', {}).get('last_update', 'N/A')
        local_hash = hashlib.md5(json.dumps(local_data, sort_keys=True).encode()).hexdigest()

    print(f"📍 Local Pipeline State: {local_update} (Hash: {local_hash[:8]})")

    # 2. Live State Probing
    live_url = f"{BASE_URL}/web/stats.json"
    print(f"📡 Probing Live Environment: {live_url}...")
    
    try:
        # Use a timestamp to bypass GitHub Pages edge cache during probe
        resp = requests.get(f"{live_url}?t={int(datetime.now().timestamp())}", timeout=10)
        if resp.status_code == 200:
            live_data = resp.json()
            live_update = live_data.get('meta', {}).get('last_update', 'PRE-SENTINEL')
            live_hash = hashlib.md5(json.dumps(live_data, sort_keys=True).encode()).hexdigest()
            
            print(f"🌍 Live Website State:  {live_update} (Hash: {live_hash[:8]})")
            
            if local_hash == live_hash:
                print("✅ SYNC STATUS: PERFECT. Live site matches Pipeline.")
            else:
                print("⚠️ SYNC STATUS: DISCREPANCY DETECTED.")
                print(f"   Delta: Live site is lagging behind Pipeline by at least 1 run.")
        else:
            print(f"⚠️ Live Probe Failed (HTTP {resp.status_code}). Site may be initializing.")
    except Exception as e:
        print(f"⚠️ Live Probe Error: {e}")

    # 3. HTML Integrity Check
    print("\n🧬 Scanning HTML Injection Points...")
    web_dir = os.path.join(base_dir, 'docs', 'web')
    for html in ['pyrite.html', 'selector.html', 'kyanite_carnelian.html']:
        path = os.path.join(web_dir, html)
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
                if "cache_bust" in content:
                    print(f"   ✅ {html.ljust(22)}: Injected successfully.")
                else:
                    print(f"   ❌ {html.ljust(22)}: MISSING cache_bust metadata.")

    # 4. Generate Telemetry for Agent
    telemetry = {
        "timestamp": datetime.now().isoformat(),
        "local_update": local_update,
        "local_hash": local_hash,
        "deployment_ready": True
    }
    with open(os.path.join(base_dir, 'docs', 'web', 'telemetry.json'), 'w') as f:
        json.dump(telemetry, f, indent=4)

    print("!"*60 + "\n")

if __name__ == "__main__":
    run_diagnostics()
