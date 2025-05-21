# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Invenio Stats Dashboard views.

This module contains the views for the Invenio Stats Dashboard.
"""

from flask import Blueprint, current_app, render_template
from invenio_communities.views.decorators import pass_community
from invenio_communities.views.communities import HEADER_PERMISSIONS
from invenio_records_resources.services.errors import PermissionDeniedError


def global_stats_dashboard():
    """Global stats dashboard view."""
    return render_template(
        current_app.config["STATS_DASHBOARD_TEMPLATES"]["global"],
        dashboard_config={
            "display_binary_sizes": not current_app.config.get(
                "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES", True
            ),
            "layout": current_app.config["STATS_DASHBOARD_LAYOUT"]["global"],
            "dashboard_type": "global",
            "default_range_options": current_app.config[
                "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS"
            ],
            **current_app.config["STATS_DASHBOARD_UI_CONFIG"]["global"],
        },
    )


@pass_community(serialize=True)
def community_stats_dashboard(pid_value, community, community_ui):
    """Community stats dashboard view."""
    permissions = community.has_permissions_to(HEADER_PERMISSIONS)
    if not permissions["can_read"]:
        raise PermissionDeniedError()

    return render_template(
        current_app.config["STATS_DASHBOARD_TEMPLATES"]["community"],
        dashboard_config={
            "display_binary_sizes": not current_app.config.get(
                "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES", True
            ),
            "layout": (
                current_app.config["STATS_DASHBOARD_LAYOUT"].get(
                    "community",
                    current_app.config["STATS_DASHBOARD_LAYOUT"]["global"],
                )
            ),
            "dashboard_type": "community",
            "default_range_options": current_app.config[
                "STATS_DASHBOARD_DEFAULT_RANGE_OPTIONS"
            ],
            **current_app.config["STATS_DASHBOARD_UI_CONFIG"]["community"],
        },
        community=community_ui,
        permissions=permissions,
    )


def create_blueprint(app):
    """Create the Invenio-Stats-Dashboard blueprint."""

    routes = app.config["STATS_DASHBOARD_ROUTES"]

    blueprint = Blueprint(
        "invenio_stats_dashboard",
        __name__,
        template_folder="../templates",
    )

    blueprint.add_url_rule(
        routes["global"],
        view_func=global_stats_dashboard,
        strict_slashes=False,
    )

    blueprint.add_url_rule(
        routes["community"],
        view_func=community_stats_dashboard,
        strict_slashes=False,
    )

    return blueprint
