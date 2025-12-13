from app.modules.auth.models import User
from app.modules.auth.services.two_factor_service import TwoFactorService  # ✅ añadido
from app.modules.profile.models import UserProfile
from core.seeders.BaseSeeder import BaseSeeder
import os
import base64


class AuthSeeder(BaseSeeder):

    priority = 1  # Higher priority

    def run(self):
        # Seeding users (skip existing emails to avoid duplicate errors)
        desired = [
            ("user1@example.com", "1234"),
            ("user2@example.com", "1234"),
            # Add a third user without 2FA by default
            ("user3@example.com", "1234"),
            ("user4@example.com", "1234"),
        ]

        users_to_create = []
        for email, password in desired:
            exists = User.query.filter_by(email=email).first()
            if not exists:
                users_to_create.append(User(email=email, password=password))

        if users_to_create:
            # Insert missing users
            self.seed(users_to_create)

        # Return the full set of users for subsequent seeding steps
        seeded_users = [User.query.filter_by(email=email).first() for email, _ in desired]
        qr_folder = os.path.join(os.getcwd(), "qrs_full")
        os.makedirs(qr_folder, exist_ok=True)

        # ✅ Activar 2FA automáticamente SOLO para usuarios listados (user1 & user2)
        users_with_2fa = {"user1@example.com", "user2@example.com"}
        for user in seeded_users:
            if user.email in users_with_2fa:
                user.two_factor_secret = TwoFactorService.generate_secret(user.email)
                user.two_factor_enabled = True
                qr_data = TwoFactorService.generate_qr_code(user.email, user.two_factor_secret)
                qr_base64 = qr_data.split(",")[1]
                img_bytes = base64.b64decode(qr_base64)
                filename = f"qr_{user.email.replace('@', '_at_')}.png"
                filepath = os.path.join(qr_folder, filename)
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
            else:
                # Ensure 2FA disabled for other seeded users
                user.two_factor_secret = None
                user.two_factor_enabled = False
        self.db.session.commit()

        # Create profiles for each user inserted (skip existing profiles)
        names = [("John", "Doe"), ("Jane", "Doe"), ("Alice", "Smith"), ("Renato", "Sanchez")]
        profiles_to_create = []
        for user, name in zip(seeded_users, names):
            # Ensure user exists (safe guard)
            if user is None:
                continue
            existing_profile = UserProfile.query.filter_by(user_id=user.id).first()
            if existing_profile:
                continue
            profile_data = {
                "user_id": user.id,
                "orcid": "",
                "affiliation": "Some University",
                "name": name[0],
                "surname": name[1],
            }
            user_profile = UserProfile(**profile_data)
            profiles_to_create.append(user_profile)

        # Seeding user profiles (only those missing)
        if profiles_to_create:
            self.seed(profiles_to_create)

        print("✅ Usuarios base creados con 2FA habilitado correctamente")
