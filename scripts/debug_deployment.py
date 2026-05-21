import os
import json
import re
import glob
from datetime import datetime

def debug_audit():
    print("\n" + "="*50)
    print("🔍 INSTITUTIONAL DEPLOYMENT AUDIT")
    print("="*50)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, 'docs')
    web_dir = os.path.join(docs_dir, 'web')
    
    # 1. Directory Structure
    print(f"\n📂 Checking paths...")
    print(f"Docs Dir Exists: {os.path.exists(docs_dir)}")
    print(f"Web Dir Exists: {os.path.exists(web_dir)}")
    print(f".nojekyll Exists: {os.path.exists(os.path.join(docs_dir, '.nojekyll'))}")

    # 2. Stats Files
    for d in [docs_dir, web_dir]:
        print(f"\n📊 Checking JSON in {os.path.basename(d) if os.path.basename(d) else 'docs'}...")
        s_path = os.path.join(d, 'stats.json')
        if os.path.exists(s_path):
            with open(s_path, 'r') as f:
                try:
                    data = json.load(f)
                    update = data.get('meta', {}).get('last_update', 'MISSING')
                    print(f"✅ stats.json: last_update = {update}")
                    # Print Pyrite ROI as benchmark
                    pyrite = data.get('models', {}).get('pyrite', {})
                    print(f"   Pyrite ROI: {pyrite.get('roi')}%")
                except Exception as e:
                    print(f"❌ stats.json: Corrupt or unreadable - {e}")
        else:
            print(f"❌ stats.json: NOT FOUND")

    # 3. HTML Injection Audit
    print(f"\n🧬 HTML Injection Audit (docs/web/*.html)...")
    html_files = glob.glob(os.path.join(web_dir, "*.html"))
    
    if not html_files:
        print("⚠️ No HTML files found in docs/web/")
    
    for html in html_files:
        filename = os.path.basename(html)
        with open(html, 'r') as f:
            content = f.read()
            # Look for DATA block
            match = re.search(r'const DATA\s*=\s*(\{.*?\});', content, re.DOTALL)
            if match:
                try:
                    # Clean up the JSON string for parsing (it might have trailing commas or JS syntax)
                    # For a simple audit, we'll just search for the strings directly to avoid JSON parse errors
                    update_match = re.search(r'"last_update":\s*"(.*?)"', match.group(1))
                    roi_match = re.search(r'"roi":\s*([\d\.-]+)', match.group(1))
                    
                    update = update_match.group(1) if update_match else "NOT FOUND"
                    roi = roi_match.group(1) if roi_match else "N/A"
                    
                    print(f"📄 {filename.ljust(20)} | Update: {update.ljust(18)} | ROI: {roi}%")
                except Exception as e:
                    print(f"📄 {filename.ljust(20)} | ❌ Error parsing DATA block: {e}")
            else:
                print(f"📄 {filename.ljust(20)} | ❌ NO DATA BLOCK FOUND")

    print("\n" + "="*50)
    print("✨ Audit Complete.")
    print("="*50 + "\n")

if __name__ == "__main__":
    debug_audit()
