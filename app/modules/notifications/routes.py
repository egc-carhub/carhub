from flask import jsonify
from flask_login import current_user, login_required

from app.extensions import db
from app.modules.notifications import notifications_bp
from app.modules.notifications.models import user_follows_user, user_follows_community, Notification
from app.modules.notifications.services import NotificationService
from app.modules.auth.models import User

notification_service = NotificationService()


@notifications_bp.route("/follow/user/<int:user_id>", methods=["POST"])
@login_required
def follow_user(user_id):
    if user_id == current_user.id:
        return jsonify({"error": "Cannot follow yourself"}), 400

    target = User.query.get(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404

    # Check if already following
    existing = (
        db.session.query(user_follows_user)
        .filter(user_follows_user.c.follower_id == current_user.id)
        .filter(user_follows_user.c.followed_id == user_id)
        .first()
    )
    if existing:
        # unfollow
        db.session.execute(
            user_follows_user.delete().where(
                (user_follows_user.c.follower_id == current_user.id)
                & (user_follows_user.c.followed_id == user_id)
            )
        )
        db.session.commit()
        return jsonify({"message": "Unfollowed", "following": False})
    else:
        db.session.execute(
            user_follows_user.insert().values(follower_id=current_user.id, followed_id=user_id)
        )
    db.session.commit()
    return jsonify({"message": "Followed", "following": True})


@notifications_bp.route("/follow/community/<int:community_id>", methods=["POST"])
@login_required
def follow_community(community_id):
    # Toggle follow on community
    existing = (
        db.session.query(user_follows_community)
        .filter(user_follows_community.c.user_id == current_user.id)
        .filter(user_follows_community.c.community_id == community_id)
        .first()
    )
    if existing:
        db.session.execute(
            user_follows_community.delete().where(
                (user_follows_community.c.user_id == current_user.id)
                & (user_follows_community.c.community_id == community_id)
            )
        )
        db.session.commit()
        return jsonify({"message": "Unfollowed community", "following": False})
    else:
        db.session.execute(
            user_follows_community.insert().values(user_id=current_user.id, community_id=community_id)
        )
    db.session.commit()
    return jsonify({"message": "Followed community", "following": True})


@notifications_bp.route("/notifications", methods=["GET"])
@login_required
def list_notifications():
    notifs = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
    data = [
        {
            "id": n.id,
            "type": n.type,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]
    return jsonify(data)


@notifications_bp.route("/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    n = Notification.query.get(notif_id)
    if not n or n.recipient_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    n.read = True
    db.session.commit()
    return jsonify({"message": "Marked read"})
