"""
database.py — Dual-backend user authentication for the Y-Strainer app.

- LOCAL  (no DATABASE_URL env var): uses SQLite — zero config, works out of the box.
- RAILWAY (DATABASE_URL set by PostgreSQL plugin): uses psycopg2 — persistent prod DB.

Passwords are hashed with PBKDF2-HMAC-SHA256 (100 000 iterations) using
Python's standard-library hashlib — no external crypto dependencies required.
"""

import hashlib
import os

# ── Shared password helpers (used by both backends) ────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, key_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return key.hex() == key_hex
    except Exception:
        return False


# ── Backend selection ──────────────────────────────────────────────────────────

_DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Railway provides postgres:// but psycopg2 requires postgresql://
if _DATABASE_URL.startswith("postgres://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql://", 1)


if _DATABASE_URL:
    # ── PostgreSQL (Railway production) ───────────────────────────────────────
    import psycopg2
    import psycopg2.errorcodes

    def _conn():
        return psycopg2.connect(_DATABASE_URL)

    def init_db() -> None:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id            SERIAL PRIMARY KEY,
                        username      TEXT UNIQUE NOT NULL,
                        email         TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()

    def create_user(username: str, email: str, password: str) -> tuple:
        try:
            with _conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                        (username.strip(), email.strip().lower(), hash_password(password)),
                    )
                conn.commit()
            return True, ""
        except psycopg2.errors.UniqueViolation as exc:
            msg = str(exc).lower()
            if "username" in msg:
                return False, "Username already taken."
            if "email" in msg:
                return False, "Email already registered."
            return False, "Registration failed."
        except psycopg2.Error:
            return False, "Registration failed."

    def get_user_by_username(username: str) -> dict | None:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, email, password_hash FROM users WHERE username = %s",
                    (username.strip(),),
                )
                row = cur.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "email": row[2], "password_hash": row[3]}
        return None

else:
    # ── SQLite (local development) ─────────────────────────────────────────────
    import sqlite3
    from pathlib import Path

    _DB_PATH = Path(__file__).parent / "users.db"

    def init_db() -> None:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT UNIQUE NOT NULL,
                    email         TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def create_user(username: str, email: str, password: str) -> tuple:
        try:
            with sqlite3.connect(_DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username.strip(), email.strip().lower(), hash_password(password)),
                )
                conn.commit()
            return True, ""
        except sqlite3.IntegrityError as exc:
            msg = str(exc).lower()
            if "username" in msg:
                return False, "Username already taken."
            if "email" in msg:
                return False, "Email already registered."
            return False, "Registration failed."

    def get_user_by_username(username: str) -> dict | None:
        with sqlite3.connect(_DB_PATH) as conn:
            row = conn.execute(
                "SELECT id, username, email, password_hash FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
        if row:
            return {"id": row[0], "username": row[1], "email": row[2], "password_hash": row[3]}
        return None
