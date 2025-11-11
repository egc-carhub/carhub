from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing
from faker import Faker

fake = Faker()


class ProfileBehavior(TaskSet):
    def on_start(self):
        # quick sanity check of homepage
        self.client.get("/")

    @task(3)
    def index(self):
        self.client.get("/")

    @task(7)
    def view_profile(self):
        # pick a random user id to simulate different public profiles
        user_id = fake.random_int(min=1, max=10)
        resp = self.client.get(f"/profile/{user_id}")
        if resp.status_code != 200:
            print(f"[locust] profile /profile/{user_id} returned {resp.status_code}")


class ProfileUser(HttpUser):
    tasks = [ProfileBehavior]
    min_wait = 1000
    max_wait = 3000
    host = get_host_for_locust_testing()
