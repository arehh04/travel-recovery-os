"""Quick status check for a mission."""
import urllib.request
import json
import sys

mission_id = sys.argv[1] if len(sys.argv) > 1 else "mission-b195c140e2c5"
try:
    r = urllib.request.urlopen(f"http://localhost:8000/api/v1/missions/{mission_id}/status", timeout=5)
    data = json.loads(r.read())
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")
