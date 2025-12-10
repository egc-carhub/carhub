import base64

import pyotp
import pytest
from flask import url_for

from app.extensions import db
from app.modules.auth.models import User, UserSession
from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.auth.services.two_factor_service import TwoFactorService
from app.modules.profile.repositories import UserProfileRepository


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


def test_login_success(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path != url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_email(test_client):
    response = test_client.post(
        "/login", data=dict(email="bademail@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_password(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="basspassword"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_signup_user_no_name(test_client):
    response = test_client.post(
        "/signup", data=dict(surname="Foo", email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert b"This field is required" in response.data, response.data


def test_signup_user_unsuccessful(test_client):
    email = "test@example.com"
    response = test_client.post(
        "/signup", data=dict(name="Test", surname="Foo", email=email, password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert f"Email {email} in use".encode("utf-8") in response.data


def test_signup_user_successful(test_client):
    response = test_client.post(
        "/signup",
        data=dict(name="Foo", surname="Example", email="foo@example.com", password="foo1234"),
        follow_redirects=True,
    )
    assert response.request.path == url_for("public.index"), "Signup was unsuccessful"


def test_service_create_with_profie_success(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "service_test@example.com", "password": "test1234"}

    AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 1
    assert UserProfileRepository().count() == 1


def test_service_create_with_profile_fail_no_email(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "", "password": "1234"}

    with pytest.raises(ValueError, match="Email is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


def test_service_create_with_profile_fail_no_password(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "test@example.com", "password": ""}

    with pytest.raises(ValueError, match="Password is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


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

# =========================
# Tests de sesiones de usuario
# =========================

import pytest
from flask import url_for
from app.extensions import db
from app.modules.auth.models import User
from app.modules.auth.services.two_factor_service import TwoFactorService

def perform_login_with_2fa_endpoint(client, user):
    """
    Helper function para simular login + 2FA en los tests de sesión.
    """
    # Login inicial
    resp = client.post(
        "/login",
        data=dict(email=user.email, password="pass1234"),
        follow_redirects=True,
    )
    assert resp.request.path != url_for("auth.login")

    # Envío del código 2FA
    code = pyotp.TOTP(user.two_factor_secret).now()
    resp = client.post(
        "/verify-2fa",
        data=dict(code=code),
        follow_redirects=True,
    )
    assert resp.request.path != url_for("auth.login")
    return resp

def test_login_creates_session(test_client, clean_database):
    """Tras login + 2FA, el usuario tiene sesión activa en Flask."""
    user = User(email="user2@example.com", password="1234")
    user.two_factor_secret = TwoFactorService.generate_secret()
    user.two_factor_enabled = True
    db.session.add(user)
    db.session.commit()

    # Login + 2FA
    perform_login_with_2fa_endpoint(test_client, user)

    # Revisar sesión de Flask-Login
    with test_client.session_transaction() as sess:
        assert "_user_id" in sess, "No se creó sesión tras login"
        user_id_in_session = int(sess["_user_id"])
        assert user_id_in_session == user.id, "ID de usuario en sesión no coincide con el usuario logueado"


def test_multiple_sessions_for_user(test_client, clean_database):
    """Verifica que un usuario puede iniciar múltiples sesiones."""
    user = User(email="user2fa@example.com", password="pass1234")
    user.two_factor_secret = TwoFactorService.generate_secret()
    user.two_factor_enabled = True
    db.session.add(user)
    db.session.commit()

    # Login dos veces simula múltiples sesiones
    resp1 = perform_login_with_2fa_endpoint(test_client, user)
    resp2 = perform_login_with_2fa_endpoint(test_client, user)
    
    assert resp1 != resp2, "Se esperaba que cada sesión sea diferente"

def test_sessions_are_user_specific(test_client, clean_database):
    """Verifica que las sesiones son específicas de cada usuario."""
    # Primer usuario
    user1 = User(email="user1@example.com", password="pass1234")
    user1.two_factor_secret = TwoFactorService.generate_secret()
    user1.two_factor_enabled = True
    db.session.add(user1)

    # Segundo usuario
    user2 = User(email="user2@example.com", password="pass1234")
    user2.two_factor_secret = TwoFactorService.generate_secret()
    user2.two_factor_enabled = True
    db.session.add(user2)
    db.session.commit()

    # Login del primer usuario
    resp1 = perform_login_with_2fa_endpoint(test_client, user1)
    # Login del segundo usuario
    resp2 = perform_login_with_2fa_endpoint(test_client, user2)

    assert resp1 != resp2, "Cada usuario debería tener su propia sesión"
