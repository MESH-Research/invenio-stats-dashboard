"""Components for invenio-stats-dashboard."""

from .components import (
    CommunityAcceptedEventComponent,
    RecordCommunityEventComponent,
    RecordCommunityEventTrackingComponent,
    update_community_events_created_date,
    update_community_events_index,
)

__all__ = [
    "CommunityAcceptedEventComponent",
    "RecordCommunityEventComponent",
    "RecordCommunityEventTrackingComponent",
    "update_community_events_index",
    "update_community_events_created_date",
]
