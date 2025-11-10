import base64

import pyotp

from app.modules.auth.services.two_factor_service import TwoFactorService
from app.modules.auth.models import User
from app.extensions import db


def test_generate_secret_qr_and_verify():
    secret = TwoFactorService.generate_secret()

    assert isinstance(secret, str)
    # pyotp.random_base32 default length is typically 16; DB allows up to 32
    assert 16 <= len(secret) <= 32

    qr = TwoFactorService.generate_qr_code("test@example.com", secret)
    assert qr.startswith("data:image/png;base64,")

    # ensure the base64 payload decodes and looks like a PNG
    payload = qr.split(",", 1)[1]
    decoded = base64.b64decode(payload)
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    # current TOTP code should verify
    code = pyotp.TOTP(secret).now()
    assert TwoFactorService.verify_code(secret, code)


def test_verify_wrong_code():
    secret = TwoFactorService.generate_secret()
    assert not TwoFactorService.verify_code(secret, "000000")


def test_enable_and_disable_2fa_on_user(test_app, clean_database):
    # create a user in the test database
    user = User(email="user2@example.com", password="pass1234")
    db.session.add(user)
    db.session.commit()

    # enable 2FA
    secret = TwoFactorService.generate_secret()
    user.two_factor_secret = secret
    user.two_factor_enabled = True
    db.session.commit()

    # verify the current code works for the saved secret
    code = pyotp.TOTP(secret).now()
    assert TwoFactorService.verify_code(user.two_factor_secret, code)

    # disabling should toggle the flag (application-level checks handle whether verification is required)
    user.two_factor_enabled = False
    db.session.commit()
    assert user.two_factor_enabled is False
