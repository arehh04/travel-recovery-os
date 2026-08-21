"""Regulatory claims and passenger rights endpoints."""

from __future__ import annotations

import datetime
import hashlib

from fastapi import APIRouter
from pydantic import BaseModel

from tros.api.db import get_connection, init_db

router = APIRouter(prefix="/claims", tags=["Claims"])


class ClaimResponse(BaseModel):
    id: str
    mission_id: str
    regulation: str
    statutory_tier: str
    amount: float
    currency: str
    status: str
    claim_letter: str
    created_at: str


@router.get("/{mission_id}", response_model=ClaimResponse)
def get_claim_for_mission(mission_id: str) -> ClaimResponse:
    """Retrieve regulatory passenger rights claim for a recovery mission."""
    init_db()
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM claims WHERE mission_id = ?", (mission_id,)).fetchone()
        if row:
            return ClaimResponse(
                id=row["id"],
                mission_id=row["mission_id"],
                regulation=row["regulation"],
                statutory_tier=row["statutory_tier"],
                amount=row["amount"],
                currency=row["currency"],
                status=row["status"],
                claim_letter=row["claim_letter"],
                created_at=row["created_at"],
            )

        # Look up mission in missions table to compute on-the-fly if not filed yet
        m_row = conn.execute("SELECT * FROM missions WHERE mission_id = ?", (mission_id,)).fetchone()
        origin = m_row["origin"] if m_row else "LHR"
        destination = m_row["destination"] if m_row else "JFK"

        # Default claim calculation
        is_eu = origin in ["LHR", "CDG", "FRA", "AMS", "MAD", "FCO"] or destination in ["LHR", "CDG", "FRA", "AMS", "MAD", "FCO"]
        is_my = origin in ["KUL", "PEN", "BKI", "KCH"] or destination in ["KUL", "PEN", "BKI", "KCH"]

        if is_eu:
            reg = "EU Regulation 261/2004 & UK261"
            tier = f"Long-haul route {origin}->{destination}"
            amount = 600.0
            curr = "EUR"
        elif is_my:
            reg = "MAVCOM MACPC 2016"
            tier = "Malaysian Passenger Protection Standard"
            amount = 300.0
            curr = "MYR"
        else:
            reg = "US DOT 14 CFR Part 259"
            tier = "DOT Passenger Refund Mandate"
            amount = 450.0
            curr = "USD"

        now_str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")
        claim_id = f"CLM-{hashlib.md5(mission_id.encode()).hexdigest()[:8].upper()}"
        claim_letter = (
            f"FORMAL NOTICE OF COMPENSATION CLAIM ({claim_id})\n"
            f"Date: {now_str}\n"
            f"Governing Authority: {reg}\n"
            f"Affected Itinerary: {origin} -> {destination}\n"
            f"Statutory Amount: {curr} {amount:.2f}\n\n"
            f"Pursuant to aviation consumer protection statutes, demand is hereby made for "
            f"statutory compensation of {curr} {amount:.2f} due to flight disruption."
        )

        return ClaimResponse(
            id=claim_id,
            mission_id=mission_id,
            regulation=reg,
            statutory_tier=tier,
            amount=amount,
            currency=curr,
            status="ELIGIBLE_READY_TO_FILE",
            claim_letter=claim_letter,
            created_at=now_str,
        )
    finally:
        conn.close()


@router.post("/{mission_id}/file", response_model=ClaimResponse)
def file_claim(mission_id: str) -> ClaimResponse:
    """Submit formal compensation claim for a mission."""
    claim = get_claim_for_mission(mission_id)
    conn = get_connection()
    try:
        now_iso = datetime.datetime.now(datetime.UTC).isoformat()
        # Ensure mission exists in missions table
        m_check = conn.execute("SELECT 1 FROM missions WHERE mission_id = ?", (mission_id,)).fetchone()
        if not m_check:
            conn.execute(
                """INSERT OR IGNORE INTO missions 
                   (mission_id, origin, destination, departure_date, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (mission_id, "LHR", "JFK", datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d"), "COMPLETED", now_iso, now_iso),
            )
        conn.execute(
            """INSERT OR REPLACE INTO claims 
               (id, mission_id, regulation, statutory_tier, amount, currency, status, claim_letter, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                claim.id,
                mission_id,
                claim.regulation,
                claim.statutory_tier,
                claim.amount,
                claim.currency,
                "SUBMITTED_TO_AIRLINE",
                claim.claim_letter,
                now_iso,
            ),
        )
        conn.commit()
        claim.status = "SUBMITTED_TO_AIRLINE"
        claim.created_at = now_iso
        return claim
    finally:
        conn.close()
