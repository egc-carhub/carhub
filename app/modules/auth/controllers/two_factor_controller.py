from flask import jsonify, request
from flask_login import current_user, login_required
from app.modules.auth.services.two_factor_service import TwoFactorService
from app.modules.auth import auth_bp
from app import db  # usa la instancia global, no app.extensions


@auth_bp.route("/enable-2fa", methods=["POST"])
@login_required
def enable_2fa():
    """Activa el segundo factor y devuelve el QR"""
    if current_user.two_factor_enabled:
        return jsonify({"message": "2FA ya está activado"}), 400

    secret = TwoFactorService.generate_secret()
    current_user.two_factor_secret = secret
    db.session.commit()

    qr = TwoFactorService.generate_qr_code(current_user.email, secret)
    return jsonify({"qr_code": qr}), 200


@auth_bp.route("/verify-2fa", methods=["POST"])
@login_required
def verify_2fa():
    """Verifica el código 2FA y lo activa definitivamente"""
    data = request.get_json()
    code = data.get("code")

    if not code:
        return jsonify({"error": "Código requerido"}), 400

    if TwoFactorService.verify_code(current_user.two_factor_secret, code):
        current_user.two_factor_enabled = True
        db.session.commit()
        return jsonify({"message": "2FA activado correctamente"}), 200

    return jsonify({"error": "Código inválido"}), 400
