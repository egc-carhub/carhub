import re

import unidecode
from sqlalchemy import and_, any_, or_

from app.modules.community.models import Community
from app.modules.dataset.models import Author, DataSet, DSMetaData, PublicationType
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from core.repositories.BaseRepository import BaseRepository


class ExploreRepository(BaseRepository):
    def __init__(self):
        super().__init__(DataSet)

    def filter(self, query="", sorting="newest", publication_type="any", tags=[], community="any", **kwargs):
        # Normalize and remove unwanted characters
        normalized_query = unidecode.unidecode(query).lower()
        cleaned_query = re.sub(r'[,.":\'()\[\]^;!¡¿?]', "", normalized_query)

        # normalize done above; no runtime logging in production

        per_word_conditions = []

        # For each search word, build an OR across multiple fields, then
        # combine those per-word OR conditions with AND so that all words
        # must be present somewhere in the dataset (but not necessarily in
        # the same field).
        words = [w for w in cleaned_query.split() if w]

        base_query = (
            self.model.query.join(DataSet.ds_meta_data)
            .join(DSMetaData.authors)
            .join(DataSet.feature_models)
            .join(FeatureModel.fm_meta_data)
            .filter(DSMetaData.dataset_doi.isnot(None))  # Exclude datasets with empty dataset_doi
        )

        # If the user provided a multi-word query, try an exact phrase match
        # first against the most relevant dataset-centric fields (description,
        # title, author name, tags). This helps when users paste a full
        # description or an author name like "Author 2" and expect a single
        # precise match.
        if cleaned_query and " " in cleaned_query:
            phrase_conditions = [
                DSMetaData.description.ilike(f"%{cleaned_query}%"),
                DSMetaData.title.ilike(f"%{cleaned_query}%"),
                Author.name.ilike(f"%{cleaned_query}%"),
                DSMetaData.tags.ilike(f"%{cleaned_query}%"),
            ]
            try:
                phrase_results = base_query.filter(or_(*phrase_conditions)).all()
                if phrase_results:
                    return phrase_results
            except Exception:
                # If phrase search fails for some reason, continue with tokenized search
                pass

        if words:
            for word in words:
                per_word_conditions.append(
                    or_(
                        DSMetaData.title.ilike(f"%{word}%"),
                        DSMetaData.description.ilike(f"%{word}%"),
                        Author.name.ilike(f"%{word}%"),
                        Author.affiliation.ilike(f"%{word}%"),
                        Author.orcid.ilike(f"%{word}%"),
                        FMMetaData.car_filename.ilike(f"%{word}%"),
                        FMMetaData.title.ilike(f"%{word}%"),
                        FMMetaData.description.ilike(f"%{word}%"),
                        FMMetaData.publication_doi.ilike(f"%{word}%"),
                        FMMetaData.tags.ilike(f"%{word}%"),
                        DSMetaData.tags.ilike(f"%{word}%"),
                    )
                )

            datasets = base_query.filter(and_(*per_word_conditions))
        else:
            # No search words: keep the base query (no additional filtering)
            datasets = base_query

        # continue with filtering

        if publication_type != "any":
            matching_type = None
            for member in PublicationType:
                if member.value.lower() == publication_type:
                    matching_type = member
                    break

            if matching_type is not None:
                datasets = datasets.filter(DSMetaData.publication_type == matching_type.name)

        if community != "any":
            datasets = datasets.join(DataSet.community_datasets).filter(Community.id == community)

        if tags:
            datasets = datasets.filter(DSMetaData.tags.ilike(any_(f"%{tag}%" for tag in tags)))

        # Order by created_at
        if sorting == "oldest":
            datasets = datasets.order_by(self.model.created_at.asc())
        else:
            datasets = datasets.order_by(self.model.created_at.desc())

        try:
            return datasets.all()
        except Exception:
            # Fall back to returning an empty list in case of unexpected DB errors
            return []
