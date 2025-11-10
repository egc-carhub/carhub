from locust import HttpUser, TaskSet, task

import os

from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token
import pyotp


class SignupBehavior(TaskSet):
    def on_start(self):
        self.signup()

    @task
    def signup(self):
        response = self.client.get("/signup")
        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/signup", data={"email": fake.email(), "password": fake.password(), "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Signup failed: {response.status_code}")


class LoginBehavior(TaskSet):
    def on_start(self):
        self.ensure_logged_out()
        self.login()

    @task
    def ensure_logged_out(self):
        response = self.client.get("/logout")
        if response.status_code != 200:
            print(f"Logout failed or no active session: {response.status_code}")

    @task
    def login(self):
        response = self.client.get("/login")
        if response.status_code != 200 or "Login" not in response.text:
            print("Already logged in or unexpected response, redirecting to logout")
            self.ensure_logged_out()
            response = self.client.get("/login")

        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/login",
            data={"email": "user1@example.com", "password": "1234", "csrf_token": csrf_token},
        )
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")
            return

        # If the app redirected to a 2FA verification page, submit a TOTP code.
        # Prefer a fixed TEST_2FA_SECRET in env for deterministic CI runs; if not
        # present we skip submission because the code rotates and may fail.
        if "id=\"code\"" in response.text or "Two-Factor Authentication" in response.text:
            secret = os.getenv("TEST_2FA_SECRET")
            if secret:
                try:
                    csrf_verify = get_csrf_token(response)
                except ValueError:
                    csrf_verify = None
                totp = pyotp.TOTP(secret)
                code = totp.now()
                post_data = {"code": code}
                if csrf_verify:
                    post_data["csrf_token"] = csrf_verify
                verify_resp = self.client.post("/verify-login-2fa", data=post_data)
                if verify_resp.status_code != 200:
                    print(f"2FA verification failed: {verify_resp.status_code}")
            else:
                print("TEST_2FA_SECRET not set; skipping 2FA code submission in locust run.")


class AuthUser(HttpUser):
    tasks = [SignupBehavior, LoginBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
