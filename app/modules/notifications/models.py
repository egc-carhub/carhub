from app.extensions import db


# Association table: users following other users
user_follows_user = db.Table(
    "user_follows_user",
    db.Column("follower_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("followed_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


# Association table: users following communities
user_follows_community = db.Table(
    "user_follows_community",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("community_id", db.Integer, db.ForeignKey("community.id"), primary_key=True),
)


class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=True)
    type = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    recipient = db.relationship("User", foreign_keys=[recipient_id], backref="notifications_received")
    actor = db.relationship("User", foreign_keys=[actor_id], backref="notifications_sent")

    def __repr__(self):
        return f"Notification<{self.id} to={self.recipient_id} type={self.type}>"
