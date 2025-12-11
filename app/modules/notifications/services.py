import logging
import threading
from flask import current_app, request
from flask_mail import Message

from app.extensions import db, mail
from app.modules.notifications.models import Notification
from app.modules.auth.models import User

logger = logging.getLogger(__name__)


def _send_async_mail(app, msg):
    # send mail in a background thread
    with app.app_context():
        try:
            # prefer the mail instance registered on the app (allows tests to inject a DummyMail
            # into current_app.extensions['mail']). Fall back to the module-level `mail` imported
            # from app.extensions if not present on the app.
            mail_obj = None
            try:
                mail_obj = app.extensions.get('mail') if getattr(app, 'extensions', None) else None
            except Exception:
                mail_obj = None

            if not mail_obj:
                mail_obj = mail

            mail_obj.send(msg)
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

    def create_and_notify(
        self,
        recipient_id: int,
        type: str,
        message: str,
        actor_id: int = None,
        dataset_id: int = None,
        community_id: int = None,
        send_email: bool = True,
    ):
        """Create a Notification row and optionally send an email to the recipient.

        Returns the Notification instance.
        """
        notif = self.create(
            recipient_id=recipient_id,
            type=type,
            message=message,
            actor_id=actor_id,
            dataset_id=dataset_id,
            community_id=community_id,
        )

        # send email asynchronously if requested and recipient has an email
        if send_email:
            try:
                recipient = User.query.get(recipient_id)
                if recipient and getattr(recipient, 'email', None):
                    subject = f"New notification from {actor_id if actor_id else 'System'}"
                    # build a simple body; include a link to the dataset if available
                    body = message
                    if dataset_id:
                        # include a full link to the dataset when possible
                        try:
                            host_url = ''
                            if request and getattr(request, 'host_url', None):
                                host_url = request.host_url.rstrip('/')
                            if host_url:
                                body += f"\n\nView: {host_url}/dataset/{dataset_id}"
                            else:
                                body += f"\n\nView: /dataset/{dataset_id}"
                        except Exception:
                            body += f"\n\nView: /dataset/{dataset_id}"
                    # delegate to the existing send_email method
                    self.send_email(recipient_email=recipient.email, subject=subject, body=body)
            except Exception:
                logger.exception("Failed scheduling email for notification")
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
