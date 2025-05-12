# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Invenio Stats Dashboard views.

This module contains the views for the Invenio Stats Dashboard.
"""

from flask import Blueprint


def create_blueprint(app):
    """Create the Invenio-Stats-Dashboard blueprint."""
    blueprint = Blueprint(
        "invenio_stats_dashboard",
        __name__,
        template_folder="../templates",
    )
    return blueprint
