# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Bookmark API for community statistics aggregators."""

from functools import wraps

import arrow
from invenio_search.utils import prefix_index
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

    def __init__(self, client, agg_type, agg_interval="day"):
        """Initialize the CommunityBookmarkAPI with a separate index."""
        super().__init__(client, agg_type, agg_interval)
        # Use a different index name to avoid conflicts with the original BookmarkAPI
        self.bookmark_index = "stats-bookmarks-community"

    @staticmethod
    def _ensure_index_exists(func):
        """Decorator for ensuring the bookmarks index exists."""

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if not Index(prefix_index(self.bookmark_index), using=self.client).exists():
                self.client.indices.create(
                    index=prefix_index(self.bookmark_index),
                    body=CommunityBookmarkAPI.MAPPINGS,
                )
            return func(self, *args, **kwargs)

        return wrapped

    @_ensure_index_exists
    def set_bookmark(self, community_id: str, value: str):
        """Set the bookmark for a community.

        This method upserts the bookmark, ensuring only one bookmark exists
        per community/aggregation type combination.
        """
        doc_id = f"{self.agg_type}_{community_id}"

        self.client.index(
            index=prefix_index(self.bookmark_index),
            id=doc_id,
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
        # Use the same document ID as set_bookmark for direct retrieval
        doc_id = f"{self.agg_type}_{community_id}"

        try:
            response = self.client.get(
                index=prefix_index(self.bookmark_index),
                id=doc_id
            )
            if response.get("found"):
                return arrow.get(response["_source"]["date"])
        except Exception:
            # Fall back to query-based approach for backward compatibility
            # in case there are old bookmarks without consistent IDs
            pass

        # Fallback: query for bookmarks (handles legacy data)
        query_bookmark = (
            Search(using=self.client, index=prefix_index(self.bookmark_index))
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

    @_ensure_index_exists
    def clear_bookmark(self, community_id: str):
        """Clear the bookmark for a specific community and aggregation type."""
        try:
            doc_id = f"{self.agg_type}_{community_id}"

            # Try to delete by ID first (more efficient for new bookmarks)
            try:
                result = self.client.delete(
                    index=prefix_index(self.bookmark_index),
                    id=doc_id
                )
                if result.get("result") == "deleted":
                    return 1
            except Exception:
                # Document doesn't exist with this ID, fall back to query-based deletion
                pass

            # Fallback: Delete all bookmarks for this community and aggregation type
            # (handles legacy data with multiple entries)
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"aggregation_type": self.agg_type}},
                            {"term": {"community_id": community_id}},
                        ]
                    }
                }
            }
            result = self.client.delete_by_query(
                index=prefix_index(self.bookmark_index),
                body=query,
                refresh=True
            )
            return result.get("deleted", 0)
        except Exception as e:
            from flask import current_app
            current_app.logger.warning(
                f"Failed to clear bookmark for {community_id}: {e}"
            )
            return 0

    @_ensure_index_exists
    def clear_all_bookmarks(
        self, community_id: str | None = None, aggregation_type: str | None = None
    ):
        """Clear bookmarks for a specific community, aggregation type, or all bookmarks.

        Args:
            community_id: If provided, only clear bookmarks for this community
            aggregation_type: If provided, only clear bookmarks for this aggregation
                type

        Returns:
            Number of bookmarks deleted
        """
        try:
            must_conditions = []
            if community_id:
                must_conditions.append({"term": {"community_id": community_id}})
            if aggregation_type:
                must_conditions.append(
                    {"term": {"aggregation_type": aggregation_type}}
                )

            query = {"query": {"bool": {"must": must_conditions}}}

            result = self.client.delete_by_query(
                index=prefix_index(self.bookmark_index),
                body=query,
                refresh=True
            )
            return result.get("deleted", 0)
        except Exception as e:
            from flask import current_app
            current_app.logger.warning(f"Failed to clear bookmarks: {e}")
            return 0

    @_ensure_index_exists
    def list_bookmarks(
        self, community_id: str | None = None, aggregation_type: str | None = None
    ):
        """List all bookmarks matching the given criteria.

        Args:
            community_id: If provided, only list bookmarks for this community
            aggregation_type: If provided, only list bookmarks for this aggregation type

        Returns:
            List of bookmark documents
        """
        try:
            must_conditions = []
            if community_id:
                must_conditions.append({"term": {"community_id": community_id}})
            if aggregation_type:
                must_conditions.append({"term": {"aggregation_type": aggregation_type}})

            query = (
                Search(using=self.client, index=prefix_index(self.bookmark_index))
                .query({"bool": {"must": must_conditions}})
                .sort({"date": {"order": "desc"}})
            )

            return [hit.to_dict() for hit in query.execute()]
        except Exception as e:
            from flask import current_app
            current_app.logger.warning(f"Failed to list bookmarks: {e}")
            return []


class CommunityEventBookmarkAPI(CommunityBookmarkAPI):
    """Bookmark API specifically for community event indexing progress.

    This tracks the furthest point of continuous community event indexing
    for each community, allowing us to distinguish between true gaps
    (missing events that should exist) and false gaps (periods where
    no events occurred because nothing happened).
    """

    def __init__(self, client, agg_interval="day"):
        """Initialize the CommunityEventBookmarkAPI."""
        super().__init__(client, "community-events-indexing", agg_interval)
