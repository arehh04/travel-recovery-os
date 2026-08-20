"""Test runner: ensures backend is up, then runs live_test.py, writes results to file."""
import json
import os
import subprocess
import sys
import time
import urllib.request

BASE = "http://localhost:8000/api/v1"
RESULTS = os.path.join(os.path.dirname(__file__), "live_test_results.txt")
log_lines = []

def log(msg):
    print(msg, flush=True)
    log_lines.append(msg)

def check_backend():
    try:
        r = urllib.request.urlopen(f"{BASE}/health", timeout=5)
        data = json.loads(r.read())
        return data.get("status") == "healthy"
    except:
        return False

def start_backend():
    log("Starting backend...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "tros.api.app:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    # Wait up to 20 seconds
    for i in range(20):
        time.sleep(1)
        if check_backend():
            log(f"Backend started after {i+1}s")
            return proc
    log("ERROR: Backend failed to start within 20s")
    # Read output for debugging
    proc.terminate()
    try:
        out, _ = proc.communicate(timeout=3)
        log(f"Backend stdout: {out.decode()[:500]}")
    except:
        pass
    return None

def main():
    log("=" * 60)
    log("LIVE SCENARIO TEST RUNNER")
    log("=" * 60)

    # Check / start backend
    backend_proc = None
    if check_backend():
        log("Backend already running and healthy")
    else:
        log("Backend not running, starting it...")
        backend_proc = start_backend()
        if not backend_proc:
            log("FATAL: Cannot start backend. Aborting.")
            with open(RESULTS, "w") as f:
                f.write("\n".join(log_lines))
            sys.exit(1)

    # Check frontend
    try:
        r = urllib.request.urlopen("http://localhost:5174/", timeout=5)
        log(f"Frontend reachable (status {r.status})")
    except:
        log("WARNING: Frontend not reachable on 5174, trying 5173...")
        try:
            r = urllib.request.urlopen("http://localhost:5173/", timeout=5)
            log(f"Frontend reachable on 5173 (status {r.status})")
        except:
            log("WARNING: Frontend not reachable on 5173 or 5174")

    # Run the test script
    log("\n" + "=" * 60)
    log("Running live_test.py...")
    log("=" * 60 + "\n")

    test_script = os.path.join(os.path.dirname(__file__), "live_test.py")
    result = subprocess.run(
        [sys.executable, test_script],
        capture_output=True,
        text=True,
        timeout=300,  # 5 minutes max
        cwd=os.path.dirname(__file__),
    )

    output = result.stdout + "\n" + result.stderr
    log(output.strip())

    # Read the results file that live_test.py wrote
    if os.path.exists(RESULTS):
        with open(RESULTS, "r", encoding="utf-8") as f:
            final_results = f.read()
        log("\n" + "=" * 60)
        log("FINAL RESULTS FROM live_test_results.txt:")
        log("=" * 60)
        log(final_results)
    else:
        log("WARNING: Results file not created")

    # Don't kill backend — let it keep running
    log("\nDone. Backend left running.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"RUNNER ERROR: {e}")
    finally:
        with open(RESULTS, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
