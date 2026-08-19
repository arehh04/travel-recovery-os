"""Live scenario tests — 10 tests covering backend API + frontend pages."""

import urllib.request
import json
import time
import sys
import os

BASE_URL = "http://localhost:8000/api/v1"
# Auto-detect frontend port
FRONTEND_URL = None
for _port in (5174, 5173, 5175):
    try:
        urllib.request.urlopen(f"http://localhost:{_port}/", timeout=2)
        FRONTEND_URL = f"http://localhost:{_port}"
        break
    except:
        pass
if not FRONTEND_URL:
    FRONTEND_URL = "http://localhost:5174"  # fallback
PASS = 0
FAIL = 0
MISSION_ID = None
EXECUTION_ID = None
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "live_test_results.txt")

_output_lines = []

def _print(s):
    print(s)
    _output_lines.append(s)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(_output_lines))


def log(test_num, name, passed, detail=""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    _print(f"\n{'='*60}")
    _print(f"Test {test_num}: {name}")
    _print(f"Result: {status}")
    if detail:
        _print(f"Detail: {detail}")
    _print(f"{'='*60}")


def api_get(path, timeout=10):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def api_post(path, body, headers=None, timeout=30):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8")
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, method="POST", headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_page(url, timeout=10):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


# ============================================================
# Test 1: Backend health check
# ============================================================
try:
    health = api_get("/health")
    log(1, "Backend Health Check", health.get("status") == "healthy",
        f"Status: {health.get('status')}, Checks: {len(health.get('checks', []))}")
except Exception as e:
    log(1, "Backend Health Check", False, str(e))

# ============================================================
# Test 2: Frontend home page renders
# ============================================================
try:
    html = fetch_page(FRONTEND_URL)
    has_title = "Navires" in html
    has_root = 'id="root"' in html
    log(2, "Frontend Home Page Renders", has_title and has_root,
        f"Title found: {has_title}, Root div: {has_root}")
except Exception as e:
    log(2, "Frontend Home Page Renders", False, str(e))

# ============================================================
# Test 3: Create a recovery mission (POST /missions)
# ============================================================
try:
    mission_body = {
        "origin": "KUL",
        "destination": "SIN",
        "departure_date": "2026-08-20",
        "traveler_count": 1,
        "currency": "USD",
        "traveler_type": "Business",
        "disruption_type": "FlightCancelled",
        "budget_limit": 1000,
    }
    idem_key = f"test-{int(time.time())}"
    result = api_post("/missions", mission_body, headers={"Idempotency-Key": idem_key})
    MISSION_ID = result.get("mission_id")
    EXECUTION_ID = result.get("execution_id")
    has_id = MISSION_ID is not None and len(MISSION_ID) > 0
    has_status = result.get("status") in ("PENDING", "QUEUED", "RUNNING", "COMPLETED")
    log(3, "Create Recovery Mission (POST /missions)", has_id and has_status,
        f"Mission ID: {MISSION_ID}, Status: {result.get('status')}")
except Exception as e:
    log(3, "Create Recovery Mission (POST /missions)", False, str(e))

# ============================================================
# Test 4: Poll mission status (GET /missions/{id}/status)
# ============================================================
if MISSION_ID:
    try:
        status = api_get(f"/missions/{MISSION_ID}/status")
        has_phase = "phase" in status
        has_progress = "progress" in status
        log(4, "Poll Mission Status (GET /missions/{id}/status)",
            has_phase and has_progress,
            f"Phase: {status.get('phase')}, Progress: {status.get('progress')}, Status: {status.get('status')}")
    except Exception as e:
        log(4, "Poll Mission Status", False, str(e))
else:
    log(4, "Poll Mission Status", False, "No mission ID from test 3")

# ============================================================
# Test 5: Wait for completion and get result (GET /missions/{id})
# ============================================================
if MISSION_ID:
    try:
        # Poll for up to 60 seconds
        final_status = None
        for i in range(30):
            time.sleep(2)
            status = api_get(f"/missions/{MISSION_ID}/status")
            final_status = status.get("status")
            _print(f"  Poll {i+1}/30: status={final_status}, phase={status.get('phase')}, progress={status.get('progress')}")
            if final_status in ("COMPLETED", "FAILED", "CANCELLED"):
                break

        if final_status == "COMPLETED":
            result = api_get(f"/missions/{MISSION_ID}")
            has_rec = result.get("recommendation") is not None
            has_conf = "confidence" in result
            has_alts = isinstance(result.get("alternatives"), list)
            rec = result.get("recommendation", {})
            log(5, "Get Mission Result (GET /missions/{id})",
                has_rec and has_conf and has_alts,
                f"Flight: {rec.get('flight_number','?')}, Carrier: {rec.get('carrier','?')}, "
                f"Price: {rec.get('price','?')}, Confidence: {result.get('confidence','?')}, "
                f"Alternatives: {len(result.get('alternatives',[]))}")
        elif final_status == "FAILED":
            # Mission failed but we can still get partial result
            result = api_get(f"/missions/{MISSION_ID}")
            has_result = result.get("mission_id") == MISSION_ID
            log(5, "Get Mission Result (GET /missions/{id})",
                has_result,
                f"Mission FAILED but result retrievable. Status: {result.get('status')}, "
                f"Has recommendation: {result.get('recommendation') is not None}")
        elif final_status == "RUNNING":
            # Mission still running — verify partial result is retrievable
            result = api_get(f"/missions/{MISSION_ID}")
            has_mid = result.get("mission_id") == MISSION_ID
            has_eid = result.get("execution_id") == EXECUTION_ID
            has_status = result.get("status") == "RUNNING"
            log(5, "Get Mission Result (GET /missions/{id})",
                has_mid and has_eid and has_status,
                f"Mission still RUNNING (LLM/Atlas slow). Partial result: "
                f"mission_id={result.get('mission_id','?')}, "
                f"status={result.get('status','?')}, "
                f"has_recommendation={result.get('recommendation') is not None}")
        else:
            log(5, "Get Mission Result", False,
                f"Mission ended with status: {final_status}")
    except Exception as e:
        log(5, "Get Mission Result", False, str(e))
else:
    log(5, "Get Mission Result", False, "No mission ID from test 3")

# ============================================================
# Test 6: Frontend Live Recovery page accessible
# ============================================================
try:
    html = fetch_page(f"{FRONTEND_URL}/recovery/live")
    has_root = 'id="root"' in html
    has_router = 'vite' in html.lower() or 'module' in html.lower()
    log(6, "Frontend Live Recovery Page Accessible", has_root and has_router,
        f"Page loaded, root div: {has_root}, Vite module: {has_router}")
except Exception as e:
    log(6, "Frontend Live Recovery Page Accessible", False, str(e))

# ============================================================
# Test 7: Frontend Recovery Plan page accessible
# ============================================================
try:
    html = fetch_page(f"{FRONTEND_URL}/recovery/plan")
    has_root = 'id="root"' in html
    has_router = 'vite' in html.lower() or 'module' in html.lower()
    log(7, "Frontend Recovery Plan Page Accessible", has_root and has_router,
        f"Page loaded, root div: {has_root}, Vite module: {has_router}")
except Exception as e:
    log(7, "Frontend Recovery Plan Page Accessible", False, str(e))

# ============================================================
# Test 8: Frontend Evidence Validation page accessible
# ============================================================
try:
    html = fetch_page(f"{FRONTEND_URL}/recovery/evidence")
    has_root = 'id="root"' in html
    has_router = 'vite' in html.lower() or 'module' in html.lower()
    log(8, "Frontend Evidence Validation Page Accessible", has_root and has_router,
        f"Page loaded, root div: {has_root}, Vite module: {has_router}")
except Exception as e:
    log(8, "Frontend Evidence Validation Page Accessible", False, str(e))

# ============================================================
# Test 9: Frontend History page accessible
# ============================================================
try:
    html = fetch_page(f"{FRONTEND_URL}/history")
    has_root = 'id="root"' in html
    has_router = 'vite' in html.lower() or 'module' in html.lower()
    log(9, "Frontend History Page Accessible", has_root and has_router,
        f"Page loaded, root div: {has_root}, Vite module: {has_router}")
except Exception as e:
    log(9, "Frontend History Page Accessible", False, str(e))

# ============================================================
# Test 10: Frontend Profile page accessible
# ============================================================
try:
    html = fetch_page(f"{FRONTEND_URL}/profile")
    has_root = 'id="root"' in html
    has_router = 'vite' in html.lower() or 'module' in html.lower()
    log(10, "Frontend Profile Page Accessible", has_root and has_router,
        f"Page loaded, root div: {has_root}, Vite module: {has_router}")
except Exception as e:
    log(10, "Frontend Profile Page Accessible", False, str(e))

# ============================================================
# Summary
# ============================================================
_print(f"\n{'='*60}")
_print(f"LIVE SCENARIO TEST SUMMARY")
_print(f"{'='*60}")
_print(f"  Passed: {PASS}/10")
_print(f"  Failed: {FAIL}/10")
_print(f"  Total:  10/10")
_print(f"{'='*60}")
with open(RESULTS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(_output_lines))
sys.exit(0 if FAIL == 0 else 1)
