"""Invenio Stats Dashboard extension."""

from flask import Blueprint

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

        # Register blueprint
        blueprint = Blueprint(
            "invenio_stats_dashboard",
            __name__,
            template_folder="templates",
            static_folder="static",
        )
        app.register_blueprint(blueprint)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith("STATS_DASHBOARD_"):
                app.config.setdefault(k, getattr(config, k))
