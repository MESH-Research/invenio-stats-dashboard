# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Components for invenio-stats-dashboard."""

from .components import (
    CommunityAcceptedEventComponent,
    CommunityCustomFieldsDefaultsComponent,
    RecordCommunityEventComponent,
    RecordCommunityEventTrackingComponent,
    update_community_events_created_date,
    update_community_events_index,
)

__all__ = [
    "CommunityAcceptedEventComponent",
    "CommunityCustomFieldsDefaultsComponent",
    "RecordCommunityEventComponent",
    "RecordCommunityEventTrackingComponent",
    "update_community_events_index",
    "update_community_events_created_date",
]
