from app.modules.car_check.repositories import CarCheckRepository
from core.services.BaseService import BaseService


class CarCheckService(BaseService):
    def __init__(self):
        super().__init__(CarCheckRepository())
