"""Invenio Stats Dashboard extension."""

from flask_menu import current_menu
from invenio_i18n import lazy_gettext as _

from . import config


class InvenioStatsDashboard:
    """Invenio Stats Dashboard extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.extensions["invenio-stats-dashboard"] = self

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith("STATS_DASHBOARD_"):
                app.config.setdefault(k, getattr(config, k))
        existing_schedule = app.config.get("CELERYBEAT_SCHEDULE", {})
        app.config["CELERYBEAT_SCHEDULE"] = {
            **existing_schedule,
            **config.COMMUNITY_STATS_CELERYBEAT_SCHEDULE,
        }
        existing_aggregations = app.config.get("STATS_AGGREGATIONS", {})
        app.config["STATS_AGGREGATIONS"] = {
            **existing_aggregations,
            **config.COMMUNITY_STATS_AGGREGATIONS,
        }


def finalize_app(app):
    """Finalize app."""
    register_menus(app)


def register_menus(app):
    """Register menu."""
    current_menu.submenu("main.stats").register(
        endpoint="invenio_stats_dashboard.global_stats_dashboard",
        text=_("Stats"),
        order=1,
    )
