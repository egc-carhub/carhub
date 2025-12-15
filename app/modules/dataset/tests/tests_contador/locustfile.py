import os

from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token

DATASET_ID = int(os.getenv("LOCUST_DATASET_ID", "4"))
LOGIN_EMAIL = os.getenv("LOCUST_USER_EMAIL", "user3@example.com")
LOGIN_PASSWORD = os.getenv("LOCUST_USER_PASSWORD", "1234")

# Variables globales para verificación
initial_downloads = 0
final_downloads = 0


# ---------- TASKSET DE DESCARGA (CARGA) ----------
class DownloadBehavior(TaskSet):
    def on_start(self):
        self.login()

    def login(self):
        resp = self.client.get("/login", name="GET /login")
        csrf = get_csrf_token(resp)

        self.client.post(
            "/login",
            data={
                "email": LOGIN_EMAIL,
                "password": LOGIN_PASSWORD,
                "csrf_token": csrf,
            },
            name="POST /login",
            allow_redirects=True,
        )

    @task
    def download_dataset(self):
        self.client.get(
            f"/dataset/download/{DATASET_ID}",
            name="GET /dataset/download/:id",
        )


# ---------- TASKSET VERIFICADOR (1 SOLO USER) ----------
class StatsBehavior(TaskSet):
    def on_start(self):
        global initial_downloads
        self.login()

        resp = self.client.get(
            f"/datasets/{DATASET_ID}/stats",
            name="GET /datasets/:id/stats (initial)",
        )
        initial_downloads = resp.json().get("downloads", 0)
        print(f"[LOCUST] Initial downloads: {initial_downloads}")

    def on_stop(self):
        global final_downloads
        resp = self.client.get(
            f"/datasets/{DATASET_ID}/stats",
            name="GET /datasets/:id/stats (final)",
        )
        final_downloads = resp.json().get("downloads", 0)

        print(f"[LOCUST] Final downloads: {final_downloads}")
        print(f"[LOCUST] Delta downloads: {final_downloads - initial_downloads}")

    def login(self):
        resp = self.client.get("/login", name="GET /login")
        csrf = get_csrf_token(resp)

        self.client.post(
            "/login",
            data={
                "email": LOGIN_EMAIL,
                "password": LOGIN_PASSWORD,
                "csrf_token": csrf,
            },
            name="POST /login",
            allow_redirects=True,
        )

    @task
    def idle(self):
        pass


# ---------- USUARIOS ----------
class DownloadUser(HttpUser):
    tasks = [DownloadBehavior]
    min_wait = 500
    max_wait = 1500
    host = get_host_for_locust_testing()
    weight = 10


class StatsUser(HttpUser):
    tasks = [StatsBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
    weight = 1
