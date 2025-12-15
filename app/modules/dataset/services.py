import hashlib
import logging
import os
import shutil
import uuid
from typing import Optional

from flask import request

from app.extensions import db
from app.modules.auth.models import User
from app.modules.auth.services import AuthenticationService
from app.modules.community.models import Community
from app.modules.dataset.models import DataSet, DSMetaData, DSViewRecord
from app.modules.dataset.repositories import (
    AuthorRepository,
    DataSetRepository,
    DOIMappingRepository,
    DSDownloadRecordRepository,
    DSMetaDataRepository,
    DSViewRecordRepository,
)
from app.modules.featuremodel.repositories import FeatureModelRepository, FMMetaDataRepository
from app.modules.hubfile.repositories import (
    HubfileDownloadRecordRepository,
    HubfileRepository,
    HubfileViewRecordRepository,
)
from app.modules.notifications.models import (
    user_follows_community,
    user_follows_user,
)
from app.modules.notifications.services import NotificationService
from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)


def calculate_checksum_and_size(file_path):
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as file:
        content = file.read()
        hash_md5 = hashlib.md5(content, usedforsecurity=False).hexdigest()
        return hash_md5, file_size


class DataSetService(BaseService):
    def __init__(self):
        super().__init__(DataSetRepository())
        self.feature_model_repository = FeatureModelRepository()
        self.author_repository = AuthorRepository()
        self.dsmetadata_repository = DSMetaDataRepository()
        self.fmmetadata_repository = FMMetaDataRepository()
        self.dsdownloadrecord_repository = DSDownloadRecordRepository()
        self.hubfiledownloadrecord_repository = HubfileDownloadRecordRepository()
        self.hubfilerepository = HubfileRepository()
        self.dsviewrecord_repostory = DSViewRecordRepository()
        self.hubfileviewrecord_repository = HubfileViewRecordRepository()

    def move_feature_models(self, dataset: DataSet):
        current_user = AuthenticationService().get_authenticated_user()
        source_dir = current_user.temp_folder()

        working_dir = os.getenv("WORKING_DIR", "")
        dest_dir = os.path.join(working_dir, "uploads", f"user_{current_user.id}", f"dataset_{dataset.id}")

        os.makedirs(dest_dir, exist_ok=True)

        for feature_model in dataset.feature_models:
            car_filename = feature_model.fm_meta_data.car_filename
            shutil.move(os.path.join(source_dir, car_filename), dest_dir)

    def get_synchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_synchronized(current_user_id)

    def get_unsynchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_unsynchronized(current_user_id)

    def get_unsynchronized_dataset(self, current_user_id: int, dataset_id: int) -> DataSet:
        return self.repository.get_unsynchronized_dataset(current_user_id, dataset_id)

    def latest_synchronized(self):
        return self.repository.latest_synchronized()

    def count_synchronized_datasets(self):
        return self.repository.count_synchronized_datasets()

    def count_feature_models(self):
        return self.feature_model_service.count_feature_models()

    def count_authors(self) -> int:
        return self.author_repository.count()

    def count_dsmetadata(self) -> int:
        return self.dsmetadata_repository.count()

    def total_dataset_downloads(self) -> int:
        return self.dsdownloadrecord_repository.total_dataset_downloads()

    def total_dataset_views(self) -> int:
        return self.dsviewrecord_repostory.total_dataset_views()

    def create_from_form(self, form, current_user) -> DataSet:
        main_author = {
            "name": f"{current_user.profile.surname}, {current_user.profile.name}",
            "affiliation": current_user.profile.affiliation,
            "orcid": current_user.profile.orcid,
        }
        try:
            logger.info(f"Creating dsmetadata...: {form.get_dsmetadata()}")
            dsmetadata = self.dsmetadata_repository.create(**form.get_dsmetadata())
            for author_data in [main_author] + form.get_authors():
                author = self.author_repository.create(commit=False, ds_meta_data_id=dsmetadata.id, **author_data)
                dsmetadata.authors.append(author)

            dataset = self.create(commit=False, user_id=current_user.id, ds_meta_data_id=dsmetadata.id)

            try:
                # Asumimos que form.community.data es una lista de IDs (strings)
                community_ids = form.community.data
                for community_id in community_ids:
                    community = Community.query.get(int(community_id))
                    if community:
                        dataset.community_datasets.append(community)
                    else:
                        logger.warning(f"Community with id {community_id} not found.")
            except Exception as e:
                logger.exception(f"Error assigning community: {e}")

            for feature_model in form.feature_models:
                car_filename = feature_model.car_filename.data
                fmmetadata = self.fmmetadata_repository.create(commit=False, **feature_model.get_fmmetadata())
                for author_data in feature_model.get_authors():
                    author = self.author_repository.create(commit=False, fm_meta_data_id=fmmetadata.id, **author_data)
                    fmmetadata.authors.append(author)

                fm = self.feature_model_repository.create(
                    commit=False, data_set_id=dataset.id, fm_meta_data_id=fmmetadata.id
                )

                # associated files in feature model
                file_path = os.path.join(current_user.temp_folder(), car_filename)
                checksum, size = calculate_checksum_and_size(file_path)

                file = self.hubfilerepository.create(
                    commit=False, name=car_filename, checksum=checksum, size=size, feature_model_id=fm.id
                )
                fm.files.append(file)
            self.repository.session.commit()

            # --- Notifications: notify users who follow this author (current_user) ---
            try:
                followers = (
                    db.session.query(User)
                    .join(user_follows_user, User.id == user_follows_user.c.follower_id)
                    .filter(user_follows_user.c.followed_id == current_user.id)
                    .all()
                )

                notification_svc = NotificationService()
                logger.info(f"Notifying {len(followers)} followers of author {current_user.id}")
                for follower in followers:
                    try:
                        notification_svc.create_and_notify(
                            recipient_id=follower.id,
                            actor_id=current_user.id,
                            dataset_id=dataset.id,
                            type="author_published_dataset",
                            message=f"{current_user.email} published dataset '{dataset.ds_meta_data.title}'",
                        )
                    except Exception:
                        logger.exception("Failed creating notification for follower")

                # Notify users who follow each community associated with the dataset
                for community in dataset.community_datasets:
                    try:
                        # followers via explicit follow action
                        community_followers = (
                            db.session.query(User)
                            .join(user_follows_community, User.id == user_follows_community.c.user_id)
                            .filter(user_follows_community.c.community_id == community.id)
                            .all()
                        )

                        # members of the community (join) — treat them as recipients as well
                        community_members = (
                            list(community.community_members) if getattr(community, "community_members", None) else []
                        )

                        # Build unique recipient ids, exclude the actor (uploader)
                        recipient_ids = {u.id for u in community_followers} | {u.id for u in community_members}
                        if current_user and getattr(current_user, "id", None) in recipient_ids:
                            recipient_ids.discard(current_user.id)

                        logger.info(
                            "Community %s: followers=%d members=%d unique_recipients=%d",
                            community.id,
                            len(community_followers),
                            len(community_members),
                            len(recipient_ids),
                        )

                        for rid in recipient_ids:
                            try:
                                notification_svc.create_and_notify(
                                    recipient_id=rid,
                                    actor_id=current_user.id,
                                    community_id=community.id,
                                    dataset_id=dataset.id,
                                    type="community_dataset_added",
                                    message=(
                                        f"A new dataset '{dataset.ds_meta_data.title}' "
                                        "was added to a community you follow"
                                    ),
                                )
                            except Exception:
                                logger.exception(
                                    "Failed creating notification for community recipient %s in community %s",
                                    rid,
                                    community.id,
                                )
                    except Exception:
                        logger.exception("Failed retrieving community followers/members for community %s", community.id)

                db.session.commit()
            except Exception as exc_notif:
                logger.exception(f"Exception while creating notifications: {exc_notif}")
                db.session.rollback()
        except Exception as exc:
            logger.info(f"Exception creating dataset from form...: {exc}")
            self.repository.session.rollback()
            raise exc
        return dataset

    def update_dsmetadata(self, id, **kwargs):
        return self.dsmetadata_repository.update(id, **kwargs)

    def get_carhub_doi(self, dataset: DataSet) -> str:
        return f"{request.host_url.rstrip('/')}/doi/{dataset.ds_meta_data.dataset_doi}"


class AuthorService(BaseService):
    def __init__(self):
        super().__init__(AuthorRepository())


class DSDownloadRecordService(BaseService):
    def __init__(self):
        super().__init__(DSDownloadRecordRepository())


class DSMetaDataService(BaseService):
    def __init__(self):
        super().__init__(DSMetaDataRepository())

    def update(self, id, **kwargs):
        return self.repository.update(id, **kwargs)

    def filter_by_doi(self, doi: str) -> Optional[DSMetaData]:
        return self.repository.filter_by_doi(doi)


class DSViewRecordService(BaseService):
    def __init__(self):
        super().__init__(DSViewRecordRepository())

    def the_record_exists(self, dataset: DataSet, user_cookie: str):
        return self.repository.the_record_exists(dataset, user_cookie)

    def create_new_record(self, dataset: DataSet, user_cookie: str) -> DSViewRecord:
        return self.repository.create_new_record(dataset, user_cookie)

    def create_cookie(self, dataset: DataSet) -> str:

        user_cookie = request.cookies.get("view_cookie")
        if not user_cookie:
            user_cookie = str(uuid.uuid4())

        existing_record = self.the_record_exists(dataset=dataset, user_cookie=user_cookie)

        if not existing_record:
            self.create_new_record(dataset=dataset, user_cookie=user_cookie)

        return user_cookie


class DOIMappingService(BaseService):
    def __init__(self):
        super().__init__(DOIMappingRepository())

    def get_new_doi(self, old_doi: str) -> str:
        doi_mapping = self.repository.get_new_doi(old_doi)
        if doi_mapping:
            return doi_mapping.dataset_doi_new
        else:
            return None


class SizeService:

    def __init__(self):
        pass

    def get_human_readable_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024**2:
            return f"{round(size / 1024, 2)} KB"
        elif size < 1024**3:
            return f"{round(size / (1024 ** 2), 2)} MB"
        else:
            return f"{round(size / (1024 ** 3), 2)} GB"
