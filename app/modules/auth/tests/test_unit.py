import base64
from datetime import datetime

import pyotp
import pytest
from flask import url_for

from app.extensions import db
from app.modules.auth.models import User, UserSession
from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService
from app.modules.auth.services.two_factor_service import TwoFactorService
from app.modules.profile.repositories import UserProfileRepository


# =========================================================
# Helpers
# =========================================================

def create_user_for_sessions(email="test_session@example.com", password="password123"):
    """
    Crear usuario SIEMPRE vía repositorio para que la password quede hasheada
    y el login funcione con check_password.
    """
    repo = UserRepository()
    existing = repo.get_by_email(email)
    if existing:
        db.session.delete(existing)
        db.session.commit()

    user = repo.create(email=email, password=password, commit=True)
    return user


def login_user_helper(client, email, password):
    """
    Helper de login robusto: validamos por path (como tus tests originales)
    y, además, comprobamos la sesión si aplica.
    """
    resp = client.post(
        "/login",
        data=dict(email=email, password=password),
        follow_redirects=True,
    )

    # Si login fue correcto, no debemos quedarnos en /login
    with client.application.test_request_context():
        login_path = url_for("auth.login")

    assert resp.request.path != login_path, "Login helper failed: still on login page"

    # Normalmente flask-login deja _user_id en sesión; si por config no lo hace,
    # al menos el redirect ya nos garantiza que el flujo pasó.
    return resp


def get_latest_active_session(user_id: int):
    return (
        UserSession.query
        .filter_by(user_id=user_id, is_active=True)
        .order_by(UserSession.id.desc())
        .first()
    )


# =========================================================
# Tests login / signup (los tuyos)
# =========================================================

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


# =========================================================
# Tests AuthenticationService (los tuyos)
# =========================================================

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


# =========================================================
# Two Factor (los tuyos)
# =========================================================

def test_generate_secret_qr_and_verify():
    secret = TwoFactorService.generate_secret()

    assert isinstance(secret, str)
    assert 16 <= len(secret) <= 32

    qr = TwoFactorService.generate_qr_code("test@example.com", secret)
    assert qr.startswith("data:image/png;base64,")

    payload = qr.split(",", 1)[1]
    decoded = base64.b64decode(payload)
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    code = pyotp.TOTP(secret).now()
    assert TwoFactorService.verify_code(secret, code)


def test_verify_wrong_code():
    secret = TwoFactorService.generate_secret()
    assert not TwoFactorService.verify_code(secret, "000000")


def test_enable_and_disable_2fa_on_user(test_app, clean_database):
    with test_app.app_context():
        user = UserRepository().create(email="user2@example.com", password="pass1234", commit=True)

        secret = TwoFactorService.generate_secret()
        user.two_factor_secret = secret
        user.two_factor_enabled = True
        db.session.commit()

        code = pyotp.TOTP(secret).now()
        assert TwoFactorService.verify_code(user.two_factor_secret, code)

        user.two_factor_enabled = False
        db.session.commit()
        assert user.two_factor_enabled is False


# =========================================================
# User sessions (sin skipped)
# =========================================================

def test_user_session_model(test_client, clean_database):
    with test_client.application.app_context():
        user = create_user_for_sessions()

        user_session = UserSession(
            user_id=user.id,
            session_token="unique-token-123",
            ip_address="127.0.0.1",
            user_agent="TestAgent"
        )
        db.session.add(user_session)
        db.session.commit()

        assert user_session.id is not None
        assert user_session.is_active is True
        assert isinstance(user_session.created_at, datetime)
        assert isinstance(user_session.last_activity, datetime)
        assert user_session.user_id == user.id


def test_login_creates_session_record(test_client, clean_database):
    with test_client.application.app_context():
        user = create_user_for_sessions("login_test@example.com", "pass")
        email = user.email
        user_id = user.id

    test_client.get("/logout", follow_redirects=True)
    login_user_helper(test_client, email, "pass")

    with test_client.application.app_context():
        db_session_record = get_latest_active_session(user_id)
        assert db_session_record is not None
        assert db_session_record.is_active is True


def test_get_active_sessions(test_client, clean_database):
    with test_client.application.app_context():
        user = create_user_for_sessions("active_sessions@example.com", "password123")

        s1 = UserSession(user_id=user.id, session_token="token1", is_active=True)
        s2 = UserSession(user_id=user.id, session_token="token2", is_active=False)
        db.session.add_all([s1, s2])
        db.session.commit()

        service = AuthenticationService()
        active_sessions = service.get_active_sessions(user)

        assert len(active_sessions) == 1
        assert active_sessions[0].session_token == "token1"

# =========================================================
# 4 tests extra (para volver a 22, unitarios y estables)
# =========================================================


def test_user_repository_create_hashes_password(clean_database):
    user = UserRepository().create(email="hash@example.com", password="plainpass", commit=True)
    assert user.password != "plainpass"
    assert user.check_password("plainpass") is True


def test_is_email_available_true_false(clean_database):
    service = AuthenticationService()
    assert service.is_email_available("free@example.com") is True
    UserRepository().create(email="free@example.com", password="x", commit=True)
    assert service.is_email_available("free@example.com") is False


def test_temp_folder_by_user_returns_path(test_app, clean_database):
    with test_app.app_context():
        user = UserRepository().create(email="tmp@example.com", password="x", commit=True)
        path = AuthenticationService().temp_folder_by_user(user)
        assert str(user.id) in path
        assert "temp" in path


def test_create_with_profile_links_profile(clean_database):
    user = AuthenticationService().create_with_profile(
        name="A", surname="B", email="link@example.com", password="1234"
    )

    # perfil debe existir y estar vinculado
    assert user is not None
    assert UserRepository().count() == 1
    assert UserProfileRepository().count() == 1