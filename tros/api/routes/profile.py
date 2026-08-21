"""Profile and loyalty account endpoints."""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tros.api.db import get_connection, init_db

router = APIRouter(prefix="/profile", tags=["Profile"])


class LoyaltyAccountModel(BaseModel):
    id: int | None = None
    program_name: str
    alliance: str
    tier_status: str
    member_number: str
    points_balance: int = 0


class UserProfileModel(BaseModel):
    user_id: str = "default_user"
    full_name: str = "Alex Mercer"
    email: str = "alex.mercer@enterprise-travel.com"
    phone: str = "+1 (555) 234-5678"
    passport_number: str = "PA98234110"
    nationality: str = "United States"
    seat_preference: str = "AISLE"
    meal_preference: str = "STANDARD"
    max_layover_hours: int = 4
    preferred_alliance: str = "Oneworld"
    updated_at: str | None = None
    loyalty_accounts: list[LoyaltyAccountModel] = Field(default_factory=list)


def _ensure_default_profile() -> None:
    """Seed default profile if table is empty."""
    init_db()
    conn = get_connection()
    try:
        row = conn.execute("SELECT user_id FROM user_profiles WHERE user_id = 'default_user'").fetchone()
        if not row:
            now_iso = datetime.datetime.now(datetime.UTC).isoformat()
            conn.execute(
                """INSERT INTO user_profiles 
                   (user_id, full_name, email, phone, passport_number, nationality,
                    seat_preference, meal_preference, max_layover_hours, preferred_alliance, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "default_user",
                    "Alex Mercer",
                    "alex.mercer@enterprise-travel.com",
                    "+1 (555) 234-5678",
                    "PA98234110",
                    "United States",
                    "AISLE",
                    "STANDARD",
                    4,
                    "Oneworld",
                    now_iso,
                ),
            )
            # Default loyalty accounts
            conn.execute(
                """INSERT INTO loyalty_accounts 
                   (user_id, program_name, alliance, tier_status, member_number, points_balance)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("default_user", "British Airways Executive Club", "Oneworld", "Gold", "BA-99482103", 145200),
            )
            conn.execute(
                """INSERT INTO loyalty_accounts 
                   (user_id, program_name, alliance, tier_status, member_number, points_balance)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("default_user", "KrisFlyer", "Star Alliance", "Elite Silver", "SQ-33821094", 42000),
            )
            conn.commit()
    finally:
        conn.close()


@router.get("", response_model=UserProfileModel)
def get_profile(user_id: str = "default_user") -> UserProfileModel:
    """Retrieve user profile with loyalty programs."""
    _ensure_default_profile()
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Profile not found")

        loyalty_rows = conn.execute("SELECT * FROM loyalty_accounts WHERE user_id = ?", (user_id,)).fetchall()
        loyalty_accounts = [
            LoyaltyAccountModel(
                id=lr["id"],
                program_name=lr["program_name"],
                alliance=lr["alliance"],
                tier_status=lr["tier_status"],
                member_number=lr["member_number"],
                points_balance=lr["points_balance"],
            )
            for lr in loyalty_rows
        ]

        return UserProfileModel(
            user_id=row["user_id"],
            full_name=row["full_name"],
            email=row["email"],
            phone=row["phone"],
            passport_number=row["passport_number"] or "",
            nationality=row["nationality"] or "",
            seat_preference=row["seat_preference"],
            meal_preference=row["meal_preference"],
            max_layover_hours=row["max_layover_hours"],
            preferred_alliance=row["preferred_alliance"],
            updated_at=row["updated_at"],
            loyalty_accounts=loyalty_accounts,
        )
    finally:
        conn.close()


@router.put("", response_model=UserProfileModel)
def update_profile(profile: UserProfileModel) -> UserProfileModel:
    """Update passenger profile details."""
    conn = get_connection()
    now_iso = datetime.datetime.now(datetime.UTC).isoformat()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO user_profiles 
               (user_id, full_name, email, phone, passport_number, nationality,
                seat_preference, meal_preference, max_layover_hours, preferred_alliance, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                profile.user_id,
                profile.full_name,
                profile.email,
                profile.phone,
                profile.passport_number,
                profile.nationality,
                profile.seat_preference,
                profile.meal_preference,
                profile.max_layover_hours,
                profile.preferred_alliance,
                now_iso,
            ),
        )
        conn.commit()
        return get_profile(profile.user_id)
    finally:
        conn.close()


@router.post("/loyalty", response_model=LoyaltyAccountModel)
def add_loyalty_account(account: LoyaltyAccountModel, user_id: str = "default_user") -> LoyaltyAccountModel:
    """Add a frequent flyer loyalty program."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO loyalty_accounts 
               (user_id, program_name, alliance, tier_status, member_number, points_balance)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                account.program_name,
                account.alliance,
                account.tier_status,
                account.member_number,
                account.points_balance,
            ),
        )
        conn.commit()
        account.id = cursor.lastrowid
        return account
    finally:
        conn.close()


@router.delete("/loyalty/{account_id}")
def delete_loyalty_account(account_id: int) -> dict[str, Any]:
    """Delete a frequent flyer program."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM loyalty_accounts WHERE id = ?", (account_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Loyalty account not found")
        return {"status": "success", "deleted_id": account_id}
    finally:
        conn.close()
