import base64
import io

import pyotp
import qrcode


class TwoFactorService:
    @staticmethod
    def generate_secret():
        """Genera un secreto TOTP aleatorio para un usuario nuevo."""
        return pyotp.random_base32()

    @staticmethod
    def generate_qr_code(email, secret):
        """
        Genera el código QR que el usuario escaneará en Google Authenticator.
        Devuelve el QR como una cadena base64 (para incrustar en HTML).
        """
        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="UVLHub")
        qr_img = qrcode.make(uri)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{qr_b64}"

    @staticmethod
    def verify_code(secret, code):
        """Verifica que el código TOTP introducido sea válido."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
