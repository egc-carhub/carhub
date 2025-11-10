from app import db


class CarCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return f"CarCheck<{self.id}>"
