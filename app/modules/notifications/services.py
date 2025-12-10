import logging
import threading
from flask import current_app
from flask_mail import Message

from app.extensions import db, mail
from app.modules.notifications.models import Notification

logger = logging.getLogger(__name__)


def _send_async_mail(app, msg):
    # send mail in a background thread
    with app.app_context():
        try:
            mail.send(msg)
        except Exception:
            logger.exception("Failed to send email")


class NotificationService:
    def __init__(self):
        pass

    def create(
        self,
        recipient_id: int,
        type: str,
        message: str,
        actor_id: int = None,
        dataset_id: int = None,
        community_id: int = None,
    ):
        notif = Notification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            dataset_id=dataset_id,
            community_id=community_id,
            type=type,
            message=message,
        )
        db.session.add(notif)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Failed to create notification")
        return notif

    def send_email(self, recipient_email: str, subject: str, body: str):
        # If mail is configured, send an email asynchronously; otherwise log
        app = current_app._get_current_object()
        if getattr(app, "extensions", None) and "mail" in app.extensions:
            try:
                msg = Message(subject=subject, recipients=[recipient_email], body=body)
                thr = threading.Thread(target=_send_async_mail, args=(app, msg), daemon=True)
                thr.start()
            except Exception:
                logger.exception("Failed to enqueue email send")
        else:
            logger.info(f"[email disabled] To: {recipient_email} Subject: {subject} Body: {body}")
