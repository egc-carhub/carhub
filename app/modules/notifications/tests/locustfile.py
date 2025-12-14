
from locust import HttpUser, TaskSet, task, between
import random
from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token

class NotificationsBehavior(TaskSet):
    def on_start(self):
        self.login()
        self.followed_community_id = None

    def login(self, email="user3@example.com", password="1234"):
        with self.client.get("/login", catch_response=True) as response:
            csrf_token = get_csrf_token(response)
            response.success()
        with self.client.post("/login", {
            "email": email,
            "password": password,
            "csrf_token": csrf_token
        }, allow_redirects=True, catch_response=True) as login_resp:
            if login_resp.status_code not in [200, 302]:
                print(f"[LOGIN] Código inesperado: {login_resp.status_code}")
            login_resp.success()

    @task(3)
    def view_notifications(self):
        with self.client.get("/notifications", headers={"Accept": "application/json"}, catch_response=True) as resp:
            if resp.status_code != 200:
                print(f"[NOTIFICATIONS] Código inesperado: {resp.status_code}")
            try:
                data = resp.json()
                if not isinstance(data, list):
                    print("[NOTIFICATIONS] Respuesta no es lista")
            except Exception:
                print("[NOTIFICATIONS] Error parseando JSON")
            resp.success()

    @task(2)
    def follow_and_unfollow_user(self):
        user_id = random.choice([1, 2, 3, 4, 5])
        with self.client.post(f"/follow/user/{user_id}", headers={"Accept": "application/json"}, catch_response=True) as resp:
            if resp.status_code not in [200, 201, 400, 404]:
                print(f"[FOLLOW USER] Código inesperado: {resp.status_code}")
            resp.success()
        with self.client.post(f"/follow/user/{user_id}", headers={"Accept": "application/json"}, catch_response=True) as resp2:
            if resp2.status_code not in [200, 201, 400, 404]:
                print(f"[UNFOLLOW USER] Código inesperado: {resp2.status_code}")
            resp2.success()

    @task(2)
    def follow_and_unfollow_community(self):
        community_id = random.choice([1, 2, 3])
        with self.client.post(f"/follow/community/{community_id}", headers={"Accept": "application/json"}, catch_response=True) as resp:
            if resp.status_code not in [200, 201, 400, 404]:
                print(f"[FOLLOW COMMUNITY] Código inesperado: {resp.status_code}")
            resp.success()
        with self.client.post(f"/follow/community/{community_id}", headers={"Accept": "application/json"}, catch_response=True) as resp2:
            if resp2.status_code not in [200, 201, 400, 404]:
                print(f"[UNFOLLOW COMMUNITY] Código inesperado: {resp2.status_code}")
            resp2.success()

    @task(2)
    def view_community_list(self):
        with self.client.get("/community/list", catch_response=True) as response:
            if response.status_code not in [200, 302, 401]:
                print(f"[COMMUNITY LIST] Código inesperado: {response.status_code}")
            response.success()

    @task(2)
    def view_specific_community(self):
        community_ids = [1, 2, 3]
        community_id = random.choice(community_ids)
        with self.client.get(f"/community/{community_id}", catch_response=True) as response:
            if response.status_code not in [200, 302, 404, 401]:
                print(f"[COMMUNITY {community_id}] Código inesperado: {response.status_code}")
            response.success()

    @task(1)
    def join_community(self):
        community_ids = [1, 2, 3]
        community_id = random.choice(community_ids)
        with self.client.post(
            f"/community/join/{community_id}",
            headers={"Accept": "application/json"},
            allow_redirects=True,
            catch_response=True
        ) as response:
            if response.status_code not in [200, 201, 400, 404, 302]:
                print(f"[JOIN COMMUNITY {community_id}] Código inesperado: {response.status_code}")
            response.success()

    @task(1)
    def leave_community(self):
        community_ids = [1, 2, 3]
        community_id = random.choice(community_ids)
        with self.client.post(
            f"/community/leave/{community_id}",
            headers={"Accept": "application/json"},
            allow_redirects=True,
            catch_response=True
        ) as response:
            if response.status_code not in [200, 201, 400, 404, 302]:
                print(f"[LEAVE COMMUNITY {community_id}] Código inesperado: {response.status_code}")
            response.success()

    @task(1)
    def mark_notification_read(self):
        notif_id = random.randint(1, 10)
        with self.client.post(f"/notifications/{notif_id}/read", headers={"Accept": "application/json"}, catch_response=True) as resp:
            if resp.status_code not in [200, 404]:
                print(f"[MARK NOTIF {notif_id} READ] Código inesperado: {resp.status_code}")
            resp.success()


class NotificationsUser(HttpUser):
    tasks = [NotificationsBehavior]
    wait_time = between(5, 10)
    host = get_host_for_locust_testing()
