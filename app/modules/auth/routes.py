from flask import jsonify, redirect, render_template, request, session, url_for, current_app
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, SignupForm
from app.modules.auth.models import UserSession
from app.modules.auth.services import AuthenticationService
from app.modules.profile.services import UserProfileService

authentication_service = AuthenticationService()
user_profile_service = UserProfileService()


@auth_bp.route("/signup/", methods=["GET", "POST"])
def show_signup_form():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        if not authentication_service.is_email_available(email):
            return render_template("auth/signup_form.html", form=form, error=f"Email {email} in use")

        try:
            user = authentication_service.create_with_profile(**form.data)
        except Exception as exc:
            return render_template("auth/signup_form.html", form=form, error=f"Error creating user: {exc}")

        # Log user
        login_user(user, remember=True)

        # Crear sesión para el nuevo usuario
        import uuid
        from datetime import datetime
        
        session_token = str(uuid.uuid4())
        user_session = UserSession(
            user_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            session_token=session_token,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )
        db.session.add(user_session)
        db.session.commit()
        session["_id"] = session_token

        return redirect(url_for("public.index"))

    return render_template("auth/signup_form.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        if authentication_service.login(form.email.data, form.password.data):
            return redirect(url_for("public.index"))

        return render_template("auth/login_form.html", form=form, error="Invalid credentials")

    return render_template("auth/login_form.html", form=form)


@auth_bp.route("/logout")
def logout():
    try:
        if current_user.is_authenticated:
            current_token = session.get("_id")
            if current_token:
                user_session = UserSession.query.filter_by(user_id=current_user.id, session_token=current_token).first()
                if user_session:
                    user_session.is_active = False
                    db.session.commit()
    except Exception as exc:
        print("Error closing user session on logout:", exc)

    logout_user()
    session.clear()
    return redirect(url_for("public.index"))


@auth_bp.before_app_request
def ensure_session_active():
    """Forzar logout si la sesión actual en la BD está marcada como inactiva."""
    try:
        if current_user.is_authenticated:
            current_token = session.get("_id")
            if not current_token:
                return None

            user_session = UserSession.query.filter_by(user_id=current_user.id, session_token=current_token).first()
            if user_session is None or not user_session.is_active:
                # Sesión invalidada desde otro dispositivo -> forzar logout aquí
                logout_user()
                session.clear()
                return redirect(url_for("public.index"))
    except Exception as exc:
        current_app.logger.exception("Error comprobando is_active de la sesión: %s", exc)
    return None


@auth_bp.route("/sessions", methods=["GET"])
@login_required
def list_sessions():
    try:
        # Usar el service pasando el objeto User; si no existe el método, usar fallback directo a la BD
        if hasattr(authentication_service, "get_active_sessions"):
            sessions = authentication_service.get_active_sessions(current_user)
        else:
            sessions = UserSession.query.filter_by(user_id=current_user.id, is_active=True).all()
    except Exception as exc:
        current_app.logger.exception("Error fetching active sessions: %s", exc)
        return jsonify([]), 500

    current_session_id = session.get("_id")

    data = [
        {
            "id": s.id,
            "ip": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_activity": s.last_activity.isoformat() if s.last_activity else None,
            "is_current": s.session_token == current_session_id,
        }
        for s in sessions
    ]

    return jsonify(data)


@auth_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    user_session = UserSession.query.get(session_id)

    if user_session is None or user_session.user_id != current_user.id:
        return jsonify({"error": "Session not found"}), 404

    # Marcar la sesión señalada como inactiva (no eliminar)
    user_session.is_active = False
    db.session.commit()

    # Si el usuario ha cerrado su propia sesión desde el mismo dispositivo,
    # hacer logout inmediato aquí
    if user_session.session_token == session.get("_id"):
        logout_user()
        session.clear()
        return jsonify({"message": "Current session closed"}), 200

    # Para los otros dispositivos, el logout se producirá cuando hagan la siguiente petición
    return jsonify({"message": "Session closed"}), 200


@auth_bp.route("/sessions", methods=["DELETE"])
@login_required
def delete_other_sessions():
    current_id = session.get("_id")
    if current_id is None:
        return jsonify({"error": "Current session id missing"}), 400

    # Marcar como inactivas todas las demás sesiones activas del usuario
    query = UserSession.query.filter(
        UserSession.user_id == current_user.id,
        UserSession.session_token != current_id,
        UserSession.is_active == True,
    )
    closed_count = query.update({"is_active": False}, synchronize_session=False)

    db.session.commit()
    return jsonify({"message": "Other sessions closed", "closed": closed_count})


@auth_bp.route("/sessions/test", methods=["GET"])
@login_required
def create_test_session():
    import uuid
    from datetime import datetime

    # Crear sesión de prueba
    test_session = UserSession(
        user_id=current_user.id,
        ip_address="127.0.0.1",
        user_agent="TestAgent",
        session_token=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
    )
    db.session.add(test_session)
    db.session.commit()

    return jsonify({"message": "Test session created", "session_id": test_session.id})
