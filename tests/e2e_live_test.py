"""Live end-to-end integration test — POST mission, poll status, get result."""

import json
import time
import urllib.request
import uuid
import sys

BASE = "http://127.0.0.1:8765/api/v1"


def api_request(method, path, data=None, headers=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    resp = urllib.request.urlopen(req, timeout=120)
    return resp.status, json.loads(resp.read())


def main():
    print("=" * 60)
    print("TR-OS Phase 8 — Live End-to-End Integration Test")
    print("=" * 60)

    # Step 1: Health check
    print("\n[1/5] Health check...")
    status, body = api_request("GET", "/health")
    assert status == 200, f"Health failed: {status}"
    assert body["status"] == "healthy"
    print(f"  Status: {body['status']}")
    for check in body["checks"]:
        print(f"  Check: {check['name']} = {check['status']}")

    # Step 2: Create mission
    print("\n[2/5] Creating mission KUL→SIN...")
    idempotency_key = str(uuid.uuid4())
    status, body = api_request(
        "POST",
        "/missions",
        data={
            "origin": "KUL",
            "destination": "SIN",
            "departure_date": "2026-08-20",
            "traveler_count": 1,
            "currency": "USD",
            "traveler_type": "Business",
            "disruption_type": "FlightCancelled",
            "budget_limit": 1000,
        },
        headers={"Idempotency-Key": idempotency_key},
    )
    assert status == 202, f"Create failed: {status}"
    mission_id = body["mission_id"]
    print(f"  Mission ID: {mission_id}")
    print(f"  Status: {body['status']}")

    # Step 3: Poll status
    print("\n[3/5] Polling status...")
    max_wait = 180
    start = time.time()
    last_phase = ""
    while time.time() - start < max_wait:
        status, body = api_request("GET", f"/missions/{mission_id}/status")
        if body["phase"] != last_phase:
            elapsed = body.get("elapsed_ms", 0) / 1000
            print(f"  Phase: {body['phase']} ({body['status']}) — {elapsed:.1f}s")
            last_phase = body["phase"]

        if body["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(3)
    else:
        print("  TIMEOUT: mission did not complete in 180s")
        sys.exit(1)

    final_status = body["status"]
    print(f"  Final: {final_status}")

    # Step 4: Get result
    print("\n[4/5] Getting result...")
    status, body = api_request("GET", f"/missions/{mission_id}")
    assert status == 200, f"Result failed: {status}"
    result = body

    print(f"  Status: {result['status']}")
    print(f"  Confidence: {result.get('confidence', 'N/A')}")

    rec = result.get("recommendation")
    if rec:
        print(f"  Recommendation: {rec.get('flight_number', 'N/A')}")
        print(f"  Carrier: {rec.get('carrier', 'N/A')}")
        print(f"  Route: {rec.get('departure', '?')} → {rec.get('arrival', '?')}")
        print(f"  Price: {rec.get('currency', '?')} {rec.get('price', '?')}")
        print(f"  Score: {rec.get('score', '?')}")
    else:
        print("  No recommendation (mission may have failed)")

    alts = result.get("alternatives", [])
    print(f"  Alternatives: {len(alts)}")

    budget = result.get("budget", {})
    print(f"  Budget: {budget}")

    recovery = result.get("recovery", {})
    print(f"  Recovery: occurred={recovery.get('occurred')}, attempts={recovery.get('attempts')}")

    meta = result.get("execution_metadata", {})
    print(f"  Duration: {meta.get('duration_ms', '?')}ms")

    # Step 5: Verify no secrets leaked
    print("\n[5/5] Security verification...")
    raw = json.dumps(result)
    assert "sk-" not in raw, "API key leaked in result!"
    assert "api_key" not in raw.lower(), "API key field leaked!"
    assert "ATLAS_AUTH" not in raw, "Atlas auth leaked!"
    print("  No secrets leaked in API response")

    # Idempotency test
    print("\n[BONUS] Idempotency test...")
    status2, body2 = api_request(
        "POST",
        "/missions",
        data={
            "origin": "KUL",
            "destination": "SIN",
            "departure_date": "2026-08-20",
            "traveler_count": 1,
            "currency": "USD",
            "traveler_type": "Business",
            "disruption_type": "FlightCancelled",
            "budget_limit": 1000,
        },
        headers={"Idempotency-Key": idempotency_key},
    )
    assert body2["mission_id"] == mission_id, "Idempotency: different mission ID returned!"
    print(f"  Same mission_id returned: {body2['mission_id']}")

    print("\n" + "=" * 60)
    print("ALL E2E TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
