import pytest
from unittest.mock import patch

from app.modules.explore.services import ExploreService


def test_service_initialization():
    with patch("app.modules.explore.services.ExploreRepository") as RepoMock:
        service = ExploreService()
        RepoMock.assert_called_once()
        assert service.repository == RepoMock()


def test_filter_defaults():
    with patch("app.modules.explore.services.ExploreRepository") as RepoMock:
        repo = RepoMock.return_value
        service = ExploreService()

        service.filter()

        repo.filter.assert_called_once_with(
            "",
            "newest",
            "any",
            [],
            "any"
        )


def test_filter_with_parameters():
    with patch("app.modules.explore.services.ExploreRepository") as RepoMock:
        repo = RepoMock.return_value
        service = ExploreService()

        service.filter(
            query="python",
            sorting="oldest",
            publication_type="article",
            tags=["ai", "ml"],
            community="developers",
        )

        repo.filter.assert_called_once_with(
            "python",
            "oldest",
            "article",
            ["ai", "ml"],
            "developers",
        )


def test_filter_with_extra_kwargs():
    with patch("app.modules.explore.services.ExploreRepository") as RepoMock:
        repo = RepoMock.return_value
        service = ExploreService()

        service.filter(query="test", page=3, limit=10)

        repo.filter.assert_called_once_with(
            "test",
            "newest",
            "any",
            [],
            "any",
            page=3,
            limit=10
        )


@pytest.mark.parametrize("tags", [[], None])
def test_filter_tag_variants(tags):
    with patch("app.modules.explore.services.ExploreRepository") as RepoMock:
        repo = RepoMock.return_value
        service = ExploreService()

        service.filter(tags=tags)

        repo.filter.assert_called_once_with(
            "",
            "newest",
            "any",
            tags if tags is not None else None,
            "any"
        )


def test_filter_returns_repository_value():
    with patch("app.modules.explore.services.ExploreRepository") as RepoMock:
        repo = RepoMock.return_value
        repo.filter.return_value = ["item1", "item2"]

        service = ExploreService()
        result = service.filter()

        assert result == ["item1", "item2"]


def test_filter_repository_error():
    with patch("app.modules.explore.services.ExploreRepository") as RepoMock:
        repo = RepoMock.return_value
        repo.filter.side_effect = Exception("DB ERROR")

        service = ExploreService()

        with pytest.raises(Exception) as exc:
            service.filter()

        assert "DB ERROR" in str(exc.value)


def test_filter_called_exactly_once():
    with patch("app.modules.explore.services.ExploreRepository") as RepoMock:
        repo = RepoMock.return_value
        service = ExploreService()

        service.filter(query="abc")

        assert repo.filter.call_count == 1
