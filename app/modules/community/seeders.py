from core.seeders.BaseSeeder import BaseSeeder

from app.modules.auth.models import User
from app.modules.community.models import Community


class CommunitySeeder(BaseSeeder):

    priority = 2  # Lower priority

    def run(self):

        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()
        user3 = User.query.filter_by(email="user3@example.com").first()

        if not user1 or not user2 or not user3:
            raise Exception("Users not found. Please seed users first.")

        data = [
            Community(
                name="Carreras",
                description="Comunidad para coches de carreras",
                created_at=self.db.func.now(),
                community_members=[user1, user2, user3]
            ),
            Community(
                name="De mercado",
                description="Comunidad para coches de mercado",
                created_at=self.db.func.now(),
                community_members=[user1, user3]
            ),
            Community(
                name="Eléctricos",
                description="Comunidad para coches eléctricos",
                created_at=self.db.func.now(),
                community_members=[user2]
            )
        ]

        self.seed(data)
