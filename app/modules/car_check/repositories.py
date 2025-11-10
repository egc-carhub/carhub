from app.modules.car_check.models import CarCheck
from core.repositories.BaseRepository import BaseRepository


class CarCheckRepository(BaseRepository):
    def __init__(self):
        super().__init__(CarCheck)
