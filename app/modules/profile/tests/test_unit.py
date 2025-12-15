import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add two users and a dataset for the owner.
    Creates:
      - user@example.com with a profile (used to test profile editing)
      - owner@example.com with a profile and one dataset (used to test public profile and dataset view)
    """
    with test_client.application.app_context():
        # user for profile edit tests
        user_test = User(email="user@example.com", password="test1234")
        db.session.add(user_test)
        db.session.commit()

        profile = UserProfile(user_id=user_test.id, name="Name", surname="Surname")
        db.session.add(profile)
        db.session.commit()

        # owner user with a dataset
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


def test_profile_edit_and_views_are_consistent(test_client):
    """Combined test that:
    - checks the profile edit page is accessible for a logged-in user
    - checks a public profile shows the user's datasets
    - checks the dataset view page links back to the uploading user's profile
    """
    # --- Part 1: profile edit page for user@example.com
    login_response = login(test_client, "user@example.com", "test1234")
    assert login_response.status_code == 200, "Login for user@example.com failed"

    response = test_client.get("/profile/edit")
    assert response.status_code == 200, "Could not access profile edit page"
    assert b"Edit profile" in response.data, "Expected 'Edit profile' content missing"

    logout(test_client)

    # --- Part 2: public profile shows owner's datasets
    owner = User.query.filter_by(email="owner@example.com").first()
    assert owner is not None, "Owner user not found in DB"

    response = test_client.get(f"/profile/{owner.id}")
    assert response.status_code == 200
    assert b"Owner Dataset" in response.data

    # --- Part 3: dataset view links to user profile (requires owner login)
    login_response = login(test_client, "owner@example.com", "ownerpass")
    assert login_response.status_code == 200, "Login for owner@example.com failed"

    dataset = DataSet.query.filter_by(user_id=owner.id).first()
    assert dataset is not None, "Dataset for owner not found"

    response = test_client.get(f"/dataset/unsynchronized/{dataset.id}/")
    assert response.status_code == 200

    expected_href = f"/profile/{owner.id}"
    assert expected_href.encode() in response.data

    logout(test_client)
