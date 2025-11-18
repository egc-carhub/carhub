from flask import jsonify, request, session, render_template, redirect, url_for
from flask_login import login_user, current_user
from app.modules.auth.models import User
from app.modules.auth.services.two_factor_service import TwoFactorService
from app.modules.auth.forms import LoginForm
from app.modules.auth import auth_bp


# -----------------------------------------------------------------------------
# LOGIN (HTML + JSON) CON SOPORTE 2FA
# -----------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"], endpoint="auth_login_2fa")
def login():
    """Inicio de sesión con soporte para 2FA (web y API JSON)."""

    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = LoginForm()

    # --- 1️⃣ GET: mostrar formulario ---
    if request.method == "GET":
        return render_template("auth/login_form.html", form=form)

    # --- 2️⃣ POST: procesar formulario o JSON ---
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        password = data.get("password")
        is_json = True
    else:
        email = form.email.data
        password = form.password.data
        is_json = False

    if not email or not password:
        msg = "Email y contraseña requeridos"
        return (
            jsonify({"error": msg}), 400
        ) if is_json else render_template("auth/login_form.html", form=form, error=msg)

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        msg = "Credenciales incorrectas"
        return (
            jsonify({"error": msg}), 401
        ) if is_json else render_template("auth/login_form.html", form=form, error=msg)

    if not user.two_factor_enabled:
        login_user(user)
        msg = "Inicio de sesión exitoso sin 2FA"
        return (
            jsonify({"message": msg}), 200
        ) if is_json else redirect(url_for("public.index"))

    session["pending_2fa_user"] = user.id

    if is_json:
        return jsonify({"message": "Código 2FA requerido"}), 202
    else:
        return redirect(url_for("auth.auth_verify_login_2fa"))


# -----------------------------------------------------------------------------
# VERIFICACIÓN DEL CÓDIGO 2FA (HTML + JSON)
# -----------------------------------------------------------------------------
@auth_bp.route("/verify-login-2fa", methods=["GET", "POST"], endpoint="auth_verify_login_2fa")
def verify_login_2fa():
    """Verifica el código TOTP y completa el login."""

    if request.method == "GET":
        return render_template("auth/verify_2fa.html")

    if request.content_type and "application/json" in request.content_type:
        data = request.get_json(silent=True) or {}
        code = data.get("code")
        is_json = True
    else:
        code = request.form.get("code")
        is_json = False

    user_id = session.get("pending_2fa_user")

    if not user_id:
        msg = "No hay login pendiente de verificación"
        return (
            jsonify({"error": msg}), 400
        ) if is_json else redirect(url_for("auth.auth_login_2fa"))

    user = User.query.get(user_id)
    if not user or not TwoFactorService.verify_code(user.two_factor_secret, code):
        msg = "Código inválido"
        return (
            jsonify({"error": msg}), 400
        ) if is_json else render_template("auth/verify_2fa.html", error=msg)

    login_user(user)
    session.pop("pending_2fa_user", None)

    msg = "Inicio de sesión completado con 2FA"
    return (
        jsonify({"message": msg}), 200
    ) if is_json else redirect(url_for("public.index"))
