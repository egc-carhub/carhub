from flask_wtf import FlaskForm
from wtforms import SubmitField


class CarCheckForm(FlaskForm):
    submit = SubmitField("Save car_check")
