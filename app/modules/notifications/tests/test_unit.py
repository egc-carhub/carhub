import time

from flask import current_app

from app import db
from app.modules.auth.models import User
from app.modules.notifications.models import Notification, user_follows_user
from app.modules.notifications.services import NotificationService


class DummyMail:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        # simple capture of message subject and recipients
        self.sent.append((msg.subject, tuple(msg.recipients)))


def login(client, email="test@example.com", password="test1234"):
    return client.post("/login", data=dict(email=email, password=password), follow_redirects=True)


def test_create_and_notify_sends_email(test_client):
    svc = NotificationService()

    with test_client.application.app_context():
        # ensure there is a recipient user
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(email="test@example.com", password="test1234")
            db.session.add(user)
            db.session.commit()

        dummy = DummyMail()
        # provide default_sender attribute expected by flask-mail.Message
        dummy.default_sender = current_app.config.get("MAIL_DEFAULT_SENDER", "no-reply@example.com")
        # inject dummy mail into Flask app extensions
        current_app.extensions["mail"] = dummy

        # call create_and_notify which should schedule an async send
        svc.create_and_notify(
            recipient_id=user.id,
            type="test",
            message="Hello via email",
            actor_id=None,
            send_email=True,
        )

        # give the background thread a moment to run
        time.sleep(0.2)

        assert len(dummy.sent) >= 1
        subjects = [s for s, r in dummy.sent]
        assert any("notification" in (s or "").lower() or "hello" in (s or "").lower() for s in subjects)

    def test_follow_user_and_receive_notification(test_client):
        with test_client.application.app_context():
            # create an author user
            author = User(email="author_user@example.com", password="pw")
            db.session.add(author)
            db.session.commit()
            author_id = author.id

        # login as test user
        rv = login(test_client)
        assert rv.status_code == 200

        # follow the author
        r1 = test_client.post(f"/follow/user/{author_id}", headers={"Accept": "application/json"})
        assert r1.status_code == 200
        d1 = r1.get_json()
        assert d1.get("following") is True

        # verify association row in DB exists
        with test_client.application.app_context():
            exists = (
                db.session.query(user_follows_user)
                .filter(user_follows_user.c.follower_id == User.query.filter_by(email="test@example.com").first().id)
                .filter(user_follows_user.c.followed_id == author_id)
                .first()
            )
            assert exists is not None

        # Simulate author publishing: create notifications for followers
        with test_client.application.app_context():
            followers = (
                db.session.query(User)
                .join(user_follows_user, User.id == user_follows_user.c.follower_id)
                .filter(user_follows_user.c.followed_id == author_id)
                .all()
            )
            for follower in followers:
                n = Notification(
                    recipient_id=follower.id,
                    actor_id=author_id,
                    type="author_published_dataset",
                    message="Author published dataset",
                )
                db.session.add(n)
            db.session.commit()

        # fetch notifications for test user
        rv = login(test_client)
        list_resp = test_client.get("/notifications")
        assert list_resp.status_code == 200
        data = list_resp.get_json()
        msgs = [n.get("message") for n in data]
        assert "Author published dataset" in msgs

        # unfollow and ensure no notification on subsequent publish
        r2 = test_client.post(f"/follow/user/{author_id}", headers={"Accept": "application/json"})
        assert r2.status_code == 200
        d2 = r2.get_json()
        assert d2.get("following") is False

        # verify association row removed
        with test_client.application.app_context():
            exists = (
                db.session.query(user_follows_user)
                .filter(user_follows_user.c.follower_id == User.query.filter_by(email="test@example.com").first().id)
                .filter(user_follows_user.c.followed_id == author_id)
                .first()
            )
            assert exists is None

        # simulate another publish
        with test_client.application.app_context():
            n2 = Notification(
                recipient_id=author_id,
                actor_id=author_id,
                type="author_published_dataset",
                message="Another publish",
            )
            db.session.add(n2)
            db.session.commit()

        rv = login(test_client)
        list_resp2 = test_client.get("/notifications")
        data2 = list_resp2.get_json()
        msgs2 = [n.get("message") for n in data2]
        assert "Another publish" not in msgs2
