from app.modules.auth.models import User
from app.modules.auth.services.two_factor_service import TwoFactorService  # ✅ añadido
from app.modules.profile.models import UserProfile
from core.seeders.BaseSeeder import BaseSeeder
import os
import base64


class AuthSeeder(BaseSeeder):

    priority = 1  # Higher priority

    def run(self):

        # Seeding users
        users = [
            User(email="user1@example.com", password="1234"),
            User(email="user2@example.com", password="1234"),
        ]

        # Inserted users with their assigned IDs are returned by `self.seed`.
        seeded_users = self.seed(users)
        qr_folder = os.path.join(os.getcwd(), "qrs_full")
        os.makedirs(qr_folder, exist_ok=True)

        # ✅ Activar 2FA automáticamente para cada usuario creado
        for user in seeded_users:
            user.two_factor_secret = TwoFactorService.generate_secret(user.email)
            user.two_factor_enabled = True
            qr_data = TwoFactorService.generate_qr_code(user.email, user.two_factor_secret)
            qr_base64 = qr_data.split(",")[1]
            img_bytes = base64.b64decode(qr_base64)
            filename = f"qr_{user.email.replace('@', '_at_')}.png"
            filepath = os.path.join(qr_folder, filename)
            with open(filepath, "wb") as f:
                f.write(img_bytes)
        self.db.session.commit()

        # Create profiles for each user inserted.
        user_profiles = []
        names = [("John", "Doe"), ("Jane", "Doe")]

        for user, name in zip(seeded_users, names):
            profile_data = {
                "user_id": user.id,
                "orcid": "",
                "affiliation": "Some University",
                "name": name[0],
                "surname": name[1],
            }
            user_profile = UserProfile(**profile_data)
            user_profiles.append(user_profile)

        # Seeding user profiles
        self.seed(user_profiles)

        print("✅ Usuarios base creados con 2FA habilitado correctamente")
