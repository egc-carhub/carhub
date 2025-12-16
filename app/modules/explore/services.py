from app.modules.explore.repositories import ExploreRepository
from core.services.BaseService import BaseService


class ExploreService(BaseService):
    def __init__(self):
        super().__init__(ExploreRepository())

    def filter(self,
               query="",
               sorting="newest",
               downloads_sorting="none",
               publication_type="any",
               tags=[],
               community="any",
               **kwargs):
        return self.repository.filter(query, sorting, downloads_sorting, publication_type, tags, community, **kwargs)