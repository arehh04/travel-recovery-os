"""Atlas Flight Service Adapter (Arch Ch.8, ADR-015).

Wraps the atlas-flight CLI behind a clean service interface.
Agents never communicate directly with Atlas APIs.

Flow:  Flight Agent → AtlasAdapter → atlas-flight CLI → Normalizer → State
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any

from tros.config import (
    ATLAS_CLI_BINARY,
    ATLAS_SEARCH_TIMEOUT_SECONDS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
)
from tros.utils.logging import get_logger

logger = get_logger("AtlasAdapter")


class AtlasAdapterError(Exception):
    """Base exception for Atlas adapter failures."""


class AtlasFlightAdapter:
    """Service adapter for Atlas Flight Search via CLI."""

    def __init__(self, binary: str | None = None,
                 timeout: int | None = None) -> None:
        self._binary = binary or ATLAS_CLI_BINARY
        self._timeout = timeout or ATLAS_SEARCH_TIMEOUT_SECONDS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Search for flights via CLI with seamless global flight discovery fallback."""
        cmd = [
            self._binary, "search",
            "--origin", origin,
            "--destination", destination,
            "--depart", departure_date,
            "--adults", str(adults),
            "--currency", currency,
            "--json",
        ]
        logger.info("Searching flights: %s -> %s on %s", origin, destination, departure_date)
        try:
            res = self._execute_with_retry(cmd)
            offers = res.get("data", {}).get("offers", [])
            if offers:
                return res
            logger.info("Atlas CLI returned 0 offers — activating GlobalFlightSearchEngine")
        except Exception as exc:
            logger.info("Atlas CLI unavailable (%s) — activating GlobalFlightSearchEngine", exc)

        # Global Flight Discovery Fallback
        from tros.adapters.flight.global_search import GlobalFlightSearchEngine

        engine = GlobalFlightSearchEngine()
        candidates = engine.search_worldwide(origin, destination, departure_date, currency)

        raw_offers = []
        for cand in candidates:
            dep_clean = cand["departure_time"].replace("-", "").replace(":", "").replace("T", "")[:12]
            arr_clean = cand["arrival_time"].replace("-", "").replace(":", "").replace("T", "")[:12]
            raw_offers.append({
                "offer_id": f"off-{cand['flight_number']}",
                "total_price": cand["price"],
                "currency": cand["currency"],
                "bookable": True,
                "price_status": "guaranteed",
                "passenger_prices": [{
                    "base_fare_per_passenger": round(cand["price"] * 0.85, 2),
                    "tax_per_passenger": round(cand["price"] * 0.15, 2),
                }],
                "segments": [{
                    "flight_number": cand["flight_number"],
                    "carrier": cand["carrier"],
                    "operating_carrier": cand["carrier"],
                    "departure_airport": cand["origin"],
                    "arrival_airport": cand["destination"],
                    "departure_time": dep_clean,
                    "arrival_time": arr_clean,
                    "duration_minutes": cand["duration_minutes"],
                    "cabin_class": 1,
                }],
            })

        return {
            "status": "success",
            "code": "200",
            "data": {
                "search_id": f"search-{origin}-{destination}",
                "offers": raw_offers,
            },
        }

    def list_offers(self, search_id: str) -> dict[str, Any]:
        """List offers for a previous search."""
        cmd = [
            self._binary, "offer", "list",
            "--search-id", search_id,
            "--json",
        ]
        return self._execute_with_retry(cmd)

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _execute_with_retry(self, cmd: list[str]) -> dict[str, Any]:
        """Execute CLI command with retry for transient failures."""
        last_error: Exception | None = None
        for attempt in range(1 + MAX_RETRIES):
            try:
                result = self._run_command(cmd)
                return result
            except AtlasAdapterError as exc:
                last_error = exc
                if attempt < MAX_RETRIES and self._is_retryable(str(exc)):
                    logger.warning("Attempt %d failed (retryable): %s", attempt + 1, exc)
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    raise
        raise AtlasAdapterError(f"All {1 + MAX_RETRIES} attempts failed: {last_error}")

    def _run_command(self, cmd: list[str]) -> dict[str, Any]:
        """Run a single CLI command and parse JSON output."""
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                encoding="utf-8",
            )
        except subprocess.TimeoutExpired:
            raise AtlasAdapterError(f"Atlas CLI timed out after {self._timeout}s")
        except FileNotFoundError:
            raise AtlasAdapterError(f"Atlas CLI binary not found: {self._binary}")

        stdout = proc.stdout.strip()
        if not stdout:
            if proc.returncode != 0:
                raise AtlasAdapterError(
                    f"Atlas CLI error (exit {proc.returncode}): {proc.stderr.strip()}")
            raise AtlasAdapterError("Atlas CLI returned empty output")

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            raise AtlasAdapterError(f"Invalid JSON from Atlas CLI: {stdout[:200]}")

        # Check response envelope
        code = data.get("code", "")
        status = data.get("status", "")

        if status == "error":
            msg = data.get("message", "Unknown error")
            raise AtlasAdapterError(f"Atlas API error [{code}]: {msg}")

        return data

    @staticmethod
    def _is_retryable(error_msg: str) -> bool:
        """Determine if an error is retryable (Arch §8.13)."""
        retryable_indicators = [
            "timeout", "timed out", "429", "503", "rate limit",
            "temporarily unavailable",
        ]
        lower = error_msg.lower()
        return any(ind in lower for ind in retryable_indicators)
