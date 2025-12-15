import base64
import io
import random

import pyotp
import qrcode


class TwoFactorService:
    @staticmethod
    def generate_secret(seed=None):
        """Genera un secreto TOTP aleatorio para un usuario nuevo."""
        rng = random.Random(seed)  # RNG controlado
        random_bytes = bytes(rng.getrandbits(8) for _ in range(20))  # tamaño típico para TOTP
        secret = base64.b32encode(random_bytes).decode().replace("=", "")
        return secret

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
