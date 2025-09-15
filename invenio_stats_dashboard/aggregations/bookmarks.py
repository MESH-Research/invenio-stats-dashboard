from functools import wraps

import arrow
from invenio_stats.bookmark import BookmarkAPI
from opensearchpy.helpers.index import Index
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search


class CommunityBookmarkAPI(BookmarkAPI):
    """Bookmark API for community statistics aggregators.

    This is a copy of the BookmarkAPI class in invenio-stats, but with the
    community_id added to the index to allow separate bookmarks for each community.
    """

    MAPPINGS = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "date": {"type": "date", "format": "date_optional_time"},
                "aggregation_type": {"type": "keyword"},
                "community_id": {"type": "keyword"},
            },
        }
    }

    @staticmethod
    def _ensure_index_exists(func):
        """Decorator for ensuring the bookmarks index exists."""

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if not Index(self.bookmark_index, using=self.client).exists():
                self.client.indices.create(
                    index=self.bookmark_index, body=CommunityBookmarkAPI.MAPPINGS
                )
            return func(self, *args, **kwargs)

        return wrapped

    @_ensure_index_exists
    def set_bookmark(self, community_id: str, value: str):
        """Set the bookmark for a community."""
        self.client.index(
            index=self.bookmark_index,
            body={
                "date": value,
                "aggregation_type": self.agg_type,
                "community_id": community_id,
            },
        )
        self.new_timestamp = None

    @_ensure_index_exists
    def get_bookmark(self, community_id: str, refresh_time=60):
        """Get last aggregation date."""
        # retrieve the oldest bookmark
        query_bookmark = (
            Search(using=self.client, index=self.bookmark_index)
            .query(
                Q(
                    "bool",
                    must=[
                        Q("term", aggregation_type=self.agg_type),
                        Q("term", community_id=community_id),
                    ],
                )
            )
            .sort({"date": {"order": "desc"}})
            .extra(size=1)  # fetch one document only
        )
        bookmark = next(iter(query_bookmark.execute()), None)
        if bookmark:
            return arrow.get(bookmark.date)


class CommunityEventBookmarkAPI(CommunityBookmarkAPI):
    """Bookmark API specifically for community event indexing progress.

    This tracks the furthest point of continuous community event indexing
    for each community, allowing us to distinguish between true gaps
    (missing events that should exist) and false gaps (periods where
    no events occurred because nothing happened).
    """

    def __init__(self, client, agg_interval="day"):
        super().__init__(client, "community-events-indexing", agg_interval)
