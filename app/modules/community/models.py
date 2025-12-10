from app import db

community_members = db.Table(
    'community_members',
    db.Column('community_id', db.Integer, db.ForeignKey('community.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class Community(db.Model):
    __tablename__ = 'community'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    community_members = db.relationship(
        'User',
        secondary=community_members,
        back_populates='communities'
    )
    datasets = db.relationship(
        'DataSet',
        secondary='community_datasets',
        back_populates='community_datasets'
    )

    def __repr__(self):
        return f'Community<{self.id}>'
