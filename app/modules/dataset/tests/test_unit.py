import uuid
from datetime import datetime

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DataSet, DSDownloadRecord, DSMetaData, PublicationType


def create_user_if_missing():
    user = User.query.filter_by(email="test@example.com").first()
    if not user:
        user = User(email="test@example.com", password="test1234")
        db.session.add(user)
        db.session.commit()
    return user


def create_dataset(title="Test Dataset", user=None):
    if user is None:
        user = create_user_if_missing()

    meta = DSMetaData(title=title, description="desc", publication_type=PublicationType.NONE)
    db.session.add(meta)
    db.session.commit()

    ds = DataSet(user_id=user.id, ds_meta_data_id=meta.id)
    db.session.add(ds)
    db.session.commit()
    return ds


def clear_downloads_for(dataset):
    DSDownloadRecord.query.filter_by(dataset_id=dataset.id).delete()
    db.session.commit()


def test_get_downloads_count_initial_zero(test_client):
    """
    A newly created dataset should report zero downloads.
    """
    dataset = create_dataset("initial-zero")
    clear_downloads_for(dataset)

    assert DSDownloadRecord.query.filter_by(dataset_id=dataset.id).count() == 0
    assert dataset.get_downloads_count() == 0


def test_create_dsdownloadrecord_increments_count(test_client):
    """
    Creating a DSDownloadRecord should increase the DB count and get_downloads_count().
    """
    dataset = create_dataset("create-increment")
    clear_downloads_for(dataset)

    record = DSDownloadRecord(dataset_id=dataset.id, download_cookie=str(uuid.uuid4()))
    db.session.add(record)
    db.session.commit()

    assert DSDownloadRecord.query.filter_by(dataset_id=dataset.id).count() == 1
    # reload dataset from DB to be safe
    ds = DataSet.query.get(dataset.id)
    assert ds.get_downloads_count() == 1


def test_multiple_dsdownloadrecords_count(test_client):
    """
    Multiple DSDownloadRecord rows should be counted correctly.
    """
    dataset = create_dataset("multiple-count")
    clear_downloads_for(dataset)

    for _ in range(3):
        db.session.add(DSDownloadRecord(dataset_id=dataset.id, download_cookie=str(uuid.uuid4())))
    db.session.commit()

    assert DSDownloadRecord.query.filter_by(dataset_id=dataset.id).count() == 3
    assert dataset.get_downloads_count() == 3


def test_downloads_are_isolated_between_datasets(test_client):
    """
    Downloads for one dataset should not affect another dataset's count.
    """
    ds1 = create_dataset("ds1")
    ds2 = create_dataset("ds2")
    clear_downloads_for(ds1)
    clear_downloads_for(ds2)

    db.session.add(DSDownloadRecord(dataset_id=ds1.id, download_cookie=str(uuid.uuid4())))
    db.session.add(DSDownloadRecord(dataset_id=ds1.id, download_cookie=str(uuid.uuid4())))
    db.session.commit()

    assert DSDownloadRecord.query.filter_by(dataset_id=ds1.id).count() == 2
    assert DSDownloadRecord.query.filter_by(dataset_id=ds2.id).count() == 0
    assert ds1.get_downloads_count() == 2
    assert ds2.get_downloads_count() == 0


def test_cleanup_between_tests(test_client):
    """
    Ensure that explicit cleanup removes records and leaves zero count.
    """
    dataset = create_dataset("cleanup-test")
    clear_downloads_for(dataset)

    db.session.add(DSDownloadRecord(dataset_id=dataset.id, download_cookie=str(uuid.uuid4())))
    db.session.commit()

    assert dataset.get_downloads_count() == 1

    # Now cleanup and assert zero
    clear_downloads_for(dataset)
    assert dataset.get_downloads_count() == 0


def test_get_downloads_count_handles_no_db(test_client, monkeypatch):
    """
    If an exception occurs when counting (e.g. DB unavailable), get_downloads_count should return 0.
    """
    dataset = create_dataset("exception-case")
    clear_downloads_for(dataset)

    def fake_count(*args, **kwargs):
        raise Exception("DB error")

    # Replace the filter_by to return an object whose count() raises
    class FakeQuery:
        def filter_by(self, *a, **k):
            return type("X", (), {"count": staticmethod(lambda: (_ for _ in ()).throw(Exception("DB error")))})()

    monkeypatch.setattr(DSDownloadRecord, "query", FakeQuery())

    # Should not raise, should return 0
    assert dataset.get_downloads_count() == 0


def test_create_and_delete_download_records(test_client):
    """
    Create records and then delete them using the repository-level delete,
    verifying counts update accordingly.
    """
    dataset = create_dataset("create-delete")
    clear_downloads_for(dataset)

    r1 = DSDownloadRecord(dataset_id=dataset.id, download_cookie=str(uuid.uuid4()))
    r2 = DSDownloadRecord(dataset_id=dataset.id, download_cookie=str(uuid.uuid4()))
    db.session.add_all([r1, r2])
    db.session.commit()

    assert dataset.get_downloads_count() == 2

    # delete one record
    DSDownloadRecord.query.filter_by(id=r1.id).delete()
    db.session.commit()
    assert dataset.get_downloads_count() == 1
