import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.profile.models import UserProfile
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType


@pytest.fixture(scope="module")
def test_client(test_client):
    # Add a second user (owner) with a dataset for viewing
    with test_client.application.app_context():
        owner = User(email="owner@example.com", password="ownerpass")
        db.session.add(owner)
        db.session.commit()

        owner_profile = UserProfile(user_id=owner.id, name="Owner", surname="User")
        db.session.add(owner_profile)
        db.session.commit()

        ds_meta = DSMetaData(
            title="Owner Dataset",
            description="A dataset by owner",
            publication_type=PublicationType.NONE,
            tags="",
        )
        db.session.add(ds_meta)
        db.session.commit()

        dataset = DataSet(user_id=owner.id, ds_meta_data_id=ds_meta.id)
        db.session.add(dataset)
        db.session.commit()

    yield test_client


def test_public_profile_shows_user_datasets(test_client):
    """Visiting /profile/<user_id> should show that user's uploaded datasets."""
    # owner id is 2 because conftest creates test@example.com as first user (id=1)
    owner = User.query.filter_by(email="owner@example.com").first()
    assert owner is not None

    response = test_client.get(f"/profile/{owner.id}")
    assert response.status_code == 200
    assert b"Owner Dataset" in response.data


def test_dataset_view_links_to_user_profile(test_client):
    """The dataset view page should link to the uploading user's profile."""
    owner = User.query.filter_by(email="owner@example.com").first()
    assert owner is not None

    # login as owner to access unsynchronized dataset view
    login_response = login(test_client, "owner@example.com", "ownerpass")
    assert login_response.status_code == 200

    # find the dataset created in fixture
    dataset = DataSet.query.filter_by(user_id=owner.id).first()
    assert dataset is not None

    response = test_client.get(f"/dataset/unsynchronized/{dataset.id}/")
    assert response.status_code == 200

    # link should point to /profile/<owner.id>
    expected_href = f"/profile/{owner.id}"
    assert expected_href.encode() in response.data

    logout(test_client)
