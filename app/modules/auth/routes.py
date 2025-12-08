from flask import redirect, render_template, request, url_for, jsonify, session
from flask_login import current_user, login_user, logout_user, login_required

from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, SignupForm
from app.modules.auth.services import AuthenticationService
from app.modules.profile.services import UserProfileService

from app.modules.auth.models import UserSession
from app.extensions import db


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
    logout_user()
    return redirect(url_for("public.index"))

@auth_bp.route("/sessions", methods=["GET"])
@login_required
def list_sessions():
    sessions = UserSession.query.filter_by(user_id=current_user.id).all()

    # DEBUG: imprime las sesiones encontradas
    print("SESSIONS QUERY RESULT:", sessions)

    current_session_id = session.get("_id")

    data = [
        {
            "id": s.id,
            "ip": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat(),
            "last_activity": s.last_activity.isoformat(),
            "is_current": s.session_token == current_session_id
        }
        for s in sessions
    ]

    # DEBUG: imprime los datos que se van a devolver
    print("DATA SENT TO FRONTEND:", data)

    return jsonify(data)

@auth_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
@login_required
def delete_session(session_id):
    user_session = UserSession.query.get(session_id)

    if user_session is None or user_session.user_id != current_user.id:
        return jsonify({"error": "Session not found"}), 404

    # Evitar borrar la sesión que está usando actualmente
    if user_session.session_token == session.get("_id"):
        return jsonify({"error": "Cannot delete current session"}), 400

    db.session.delete(user_session)
    db.session.commit()

    return jsonify({"message": "Session closed"})

@auth_bp.route("/sessions", methods=["DELETE"])
@login_required
def delete_other_sessions():
    current_id = session.get("_id")

    UserSession.query.filter(
        UserSession.user_id == current_user.id,
        UserSession.session_token != current_id
    ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify({"message": "Other sessions closed"})

@auth_bp.route("/sessions/test", methods=["GET"])
@login_required
def create_test_session():
    from datetime import datetime
    import uuid

    # Crear sesión de prueba
    test_session = UserSession(
        user_id=current_user.id,
        ip_address="127.0.0.1",
        user_agent="TestAgent",
        session_token=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        last_activity=datetime.utcnow()
    )
    db.session.add(test_session)
    db.session.commit()

    return jsonify({
        "message": "Test session created",
        "session_id": test_session.id
    })
