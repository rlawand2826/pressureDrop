"""
Admin script to create user accounts.

Run this locally (or on Railway shell) to add authorized users.
No one can self-register — only accounts created here can log in.

Usage:
    python add_user.py <username> <email> <password>

Examples:
    python add_user.py client1 client1@company.com MySecurePass123
    python add_user.py john john@example.com Pass@2026
"""

import sys
from pathlib import Path

# Make sure imports resolve when run from any directory
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, create_user


def main():
    if len(sys.argv) != 4:
        print("Usage: python add_user.py <username> <email> <password>")
        print("Example: python add_user.py client1 client@company.com MyPass123")
        sys.exit(1)

    username, email, password = sys.argv[1], sys.argv[2], sys.argv[3]

    if len(password) < 6:
        print("Error: Password must be at least 6 characters.")
        sys.exit(1)

    init_db()
    ok, msg = create_user(username, email, password)

    if ok:
        print(f"[OK] User '{username}' created successfully.")
        print(f"     They can now log in at your app URL with this password.")
    else:
        print(f"[ERROR] {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
