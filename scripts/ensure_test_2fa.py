"""Small helper to ensure the test user has a deterministic 2FA secret.

Usage:
    python scripts/ensure_test_2fa.py

This will connect to the application's database (via the app factory), find or create
`user1@example.com`, set a fixed TOTP secret and enable 2FA.

Do NOT run this against production databases.
"""
import os
import sys

from app import create_app, db
from app.modules.auth.models import User

# A deterministic base32 secret for tests. Replace if you prefer another value.
FIXED_SECRET = os.getenv("TEST_2FA_SECRET", "IKSV4HGLAEA67GOOENINW4PGZXPU4YQC")


def main():
    app = create_app(os.getenv("FLASK_CONFIG", "testing"))
    with app.app_context():
        user = User.query.filter_by(email="user1@example.com").first()
        if not user:
            print("Test user not found: creating user1@example.com with default password '1234'.")
            user = User(email="user1@example.com", password="1234")
            db.session.add(user)
            db.session.commit()

        user.two_factor_secret = FIXED_SECRET
        user.two_factor_enabled = True
        db.session.add(user)
        db.session.commit()

        print(f"Set 2FA secret for {user.email} to: {FIXED_SECRET}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Error ensuring test 2FA:", exc)
        sys.exit(1)
