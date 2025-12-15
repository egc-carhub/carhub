import os
import base64
from app import create_app, db
from app.modules.auth.models import User
from app.modules.auth.services.two_factor_service import TwoFactorService
from app.modules.auth.seeders import AuthSeeder
from app.modules.dataset.seeders import DataSetSeeder

# Secretos fijos para evitar inconsistencias entre equipos
FIXED_SECRETS = {
    "user1@example.com": "IKSV4HGLAEA67GOOENINW4PGZXPU4YQC",
    "user2@example.com": "7ZB2A5KOVOTUZHBYJSYIIDMBGDCLZNK5",
}

app = create_app()

with app.app_context():
    print("🧹 Reiniciando base de datos completa...")
    db.drop_all()
    db.create_all()

    print("📦 Ejecutando seeders base del sistema...")
    auth_seeder = AuthSeeder()
    dataset_seeder = DataSetSeeder()

    auth_seeder.run()
    dataset_seeder.run()

    print("\n🔐 Activando Two-Factor Authentication (2FA) en los usuarios base...")

    users = User.query.all()
    qr_folder = os.path.join(os.getcwd(), "qrs_full")
    os.makedirs(qr_folder, exist_ok=True)

    # Activar 2FA SOLO para los usuarios con secretos fijos (FIXED_SECRETS)
    for user in users:
        if user.email in FIXED_SECRETS:
            # Usa el secreto fijo
            secret = FIXED_SECRETS[user.email]
            user.two_factor_secret = secret
            user.two_factor_enabled = True

            # Generar el QR correspondiente
            qr_data = TwoFactorService.generate_qr_code(user.email, user.two_factor_secret)
            qr_base64 = qr_data.split(",")[1]
            img_bytes = base64.b64decode(qr_base64)

            filename = f"qr_{user.email.replace('@', '_at_')}.png"
            filepath = os.path.join(qr_folder, filename)

            with open(filepath, "wb") as f:
                f.write(img_bytes)

            print(f"--- {user.email} ---")
            print(f"URI: otpauth://totp/UVLHub:{user.email}?secret={user.two_factor_secret}&issuer=UVLHub")
            print(f"🔑 Secreto: {user.two_factor_secret}")
            print(f"🖼️ QR guardado en: {filepath}\n")
        else:
            # Ensure other users don't get 2FA enabled by this script
            user.two_factor_secret = None
            user.two_factor_enabled = False

    db.session.commit()
    print("✅ Base de datos restaurada con datasets y usuarios 2FA activados correctamente (secretos fijos).")
