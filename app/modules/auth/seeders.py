from app.modules.auth.models import User
from app.modules.profile.models import UserProfile
from app.modules.auth.services.two_factor_service import TwoFactorService  # ✅ añadido
from core.seeders.BaseSeeder import BaseSeeder


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

        # ✅ Activar 2FA automáticamente para cada usuario creado
        for user in seeded_users:
            user.two_factor_secret = TwoFactorService.generate_secret()
            user.two_factor_enabled = True
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
