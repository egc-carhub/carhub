import time

from flask import current_app

from app.modules.notifications.services import NotificationService
from app.modules.auth.models import User
from app import db


class DummyMail:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        # simple capture of message subject and recipients
        self.sent.append((msg.subject, tuple(msg.recipients)))


def login(client, email='test@example.com', password='test1234'):
    return client.post('/login', data=dict(email=email, password=password), follow_redirects=True)


def test_create_and_notify_sends_email(test_client):
    svc = NotificationService()

    with test_client.application.app_context():
        # ensure there is a recipient user
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            user = User(email='test@example.com', password='test1234')
            db.session.add(user)
            db.session.commit()

        dummy = DummyMail()
        # provide default_sender attribute expected by flask-mail.Message
        dummy.default_sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'no-reply@example.com')
        # inject dummy mail into Flask app extensions
        current_app.extensions['mail'] = dummy

        # call create_and_notify which should schedule an async send
        svc.create_and_notify(
            recipient_id=user.id,
            type='test',
            message='Hello via email',
            actor_id=None,
            send_email=True,
        )

        # give the background thread a moment to run
        time.sleep(0.2)

        assert len(dummy.sent) >= 1
        subjects = [s for s, r in dummy.sent]
        assert any('notification' in (s or '').lower() or 'hello' in (s or '').lower() for s in subjects)
