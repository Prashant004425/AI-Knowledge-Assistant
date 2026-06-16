import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_FILE = BASE_DIR / "data" / "user_profile.json"
DEFAULT_AVATAR = (
    "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde"
    "?auto=format&fit=crop&w=400&q=80"
)
VALID_ROLES = {"Engineer", "Admin", "User"}

DEFAULT_PROFILE: Dict[str, Any] = {
    "avatar_url": DEFAULT_AVATAR,
    "name": "Alex Morgan",
    "employee_id": "EMP-1001",
    "department": "Product Engineering",
    "email": "alex.morgan@example.com",
    "role": "Engineer",
    "joining_date": "2024-01-02",
    "about_me": "Experienced AI engineer building knowledge-first applications and intelligent search experiences.",
    "password_hash": None,
}


def _ensure_profile_file() -> None:
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PROFILE_FILE.exists():
        DEFAULT_PROFILE["password_hash"] = _hash_password("changeme")
        _save_profile(DEFAULT_PROFILE)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_profile() -> Dict[str, Any]:
    _ensure_profile_file()
    with PROFILE_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data


def _save_profile(profile: Dict[str, Any]) -> None:
    with PROFILE_FILE.open("w", encoding="utf-8") as handle:
        json.dump(profile, handle, indent=2)


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email))


def _validate_date(date_string: str) -> bool:
    try:
        datetime.fromisoformat(date_string)
        return True
    except ValueError:
        return False


def _validate_role(candidate: str) -> bool:
    return candidate in VALID_ROLES


def get_profile() -> Dict[str, Any]:
    profile = _load_profile()
    return {
        "avatar_url": profile.get("avatar_url", DEFAULT_AVATAR),
        "name": profile.get("name", ""),
        "employee_id": profile.get("employee_id", ""),
        "department": profile.get("department", ""),
        "email": profile.get("email", ""),
        "role": profile.get("role", "User"),
        "joining_date": profile.get("joining_date", ""),
        "about_me": profile.get("about_me", ""),
    }


def update_profile(updates: Dict[str, Any]) -> Dict[str, Any]:
    profile = _load_profile()

    if "email" in updates:
        email = updates["email"].strip()
        if not _validate_email(email):
            raise ValueError("The provided email address is not valid.")
        profile["email"] = email

    if "joining_date" in updates:
        joining_date = updates["joining_date"].strip()
        if not _validate_date(joining_date):
            raise ValueError("Joining date must be in YYYY-MM-DD format.")
        profile["joining_date"] = joining_date

    if "role" in updates:
        role = updates["role"].strip()
        if not _validate_role(role):
            raise ValueError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}.")
        profile["role"] = role

    for field in ["avatar_url", "name", "employee_id", "department", "about_me"]:
        if field in updates:
            profile[field] = updates[field].strip()

    _save_profile(profile)
    return get_profile()


def change_password(current_password: str, new_password: str) -> bool:
    profile = _load_profile()
    stored_hash = profile.get("password_hash")
    if stored_hash is None:
        raise ValueError("Password storage is corrupted. Please reset the profile.")

    if _hash_password(current_password) != stored_hash:
        raise ValueError("Current password is incorrect.")

    if len(new_password.strip()) < 8:
        raise ValueError("New password must be at least 8 characters long.")

    profile["password_hash"] = _hash_password(new_password)
    _save_profile(profile)
    return True


def logout_profile() -> bool:
    # Local logout is a no-op for the current application, but the endpoint exists for UX consistency.
    return True
