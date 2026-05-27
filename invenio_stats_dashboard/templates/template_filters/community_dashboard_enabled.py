# Part of invenio-stats-dashboard
# Copyright (C) 2023-2026, MESH Research
#
# invenio-stats-dashboard is free software; you can redistribute and/or
# modify it under the terms of the MIT License; see LICENSE file for more details.

from flask import current_app


def community_stats_dashboard_enabled(community_ui: dict) -> bool:
    """Determine whether a given community's stats dashboard is enabled.

    Arguments:
        community_ui: The community's metadata as a dictionary. (The result of
        the community search result's to_dict() method.)

    Returns:
        Bool: True if community stats are enabled for the InvenioRDM instance
            and either the specific community has enabled its dashboard or
            the instance is configured not to allow communities to opt out.
    """
    if not current_app.config.get("COMMUNITY_STATS_ENABLED", True):
        return False

    if not current_app.config.get("STATS_DASHBOARD_ENABLED_COMMUNITY", False):
        return False

    if not current_app.config.get("STATS_DASHBOARD_COMMUNITY_OPT_IN", True):
        return True

    custom_fields = community_ui.get("custom_fields") or {}
    return bool(custom_fields.get("stats:dashboard_enabled"))
