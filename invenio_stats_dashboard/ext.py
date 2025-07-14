"""Invenio Stats Dashboard extension."""

from flask import Flask
from flask_menu import current_menu
from invenio_i18n import lazy_gettext as _
from invenio_search.proxies import current_search

from . import config
from .components import (
    CommunityAcceptedEventComponent,
    RecordCommunityEventComponent,
    RecordCommunityEventTrackingComponent,
)
from .service import CommunityStatsService, EventReindexingService


def _ensure_templates_registered(app: Flask) -> None:
    """Ensure that all invenio_stats_dashboard templates are registered.

    This function checks if the templates for our custom aggregations are
    registered with OpenSearch. If they're not, it registers them. This is
    necessary when the invenio_stats_dashboard package is added to an existing
    instance that already has a search domain set up.
    """
    try:
        aggregations = config.COMMUNITY_STATS_AGGREGATIONS

        missing_templates = []

        for agg_name, agg_config in aggregations.items():
            template_path = agg_config.get("templates")
            if template_path:
                try:
                    app.logger.info(f"Registering template from path: {template_path}")
                    current_search.register_templates(template_path)
                except Exception as e:
                    app.logger.warning(
                        f"Failed to register template {template_path}: {e}"
                    )
                    missing_templates.append(template_path)

        # Then, put all registered index templates to OpenSearch
        try:
            app.logger.info("Putting all registered index templates to OpenSearch")

            # Debug: Check what index templates are registered
            app.logger.info(
                f"Registered index templates: "
                f"{list(current_search.index_templates.keys())}"
            )

            # Put index templates (this is where our KCWorks templates are)
            put_index_results = current_search.put_index_templates()
            app.logger.info(f"put_index_templates() returned: {put_index_results}")

            index_template_count = 0
            for template_name, response in put_index_results:
                app.logger.info(
                    f"Successfully registered index template: {template_name}"
                )
                index_template_count += 1

            if index_template_count == 0:
                app.logger.warning("No index templates were put to OpenSearch")
            else:
                app.logger.info(
                    f"Successfully put {index_template_count} index templates "
                    f"to OpenSearch"
                )

            app.logger.info("All invenio_stats_dashboard templates are registered")
        except Exception as e:
            app.logger.error(f"Failed to put index templates to OpenSearch: {e}")

        # Log warnings for any templates that failed to register
        if missing_templates:
            app.logger.warning(
                f"Failed to register {len(missing_templates)} templates: "
                f"{missing_templates}"
            )

    except Exception as e:
        app.logger.error(f"Error during template registration check: {e}")


class InvenioStatsDashboard:
    """Invenio Stats Dashboard extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        self.service = CommunityStatsService(app)
        self.event_reindexing_service = EventReindexingService(app)
        app.extensions["invenio-stats-dashboard"] = self

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith("STATS_DASHBOARD_"):
                app.config.setdefault(k, getattr(config, k))
        existing_schedule = app.config.get("CELERY_BEAT_SCHEDULE", {})
        app.config["CELERY_BEAT_SCHEDULE"] = {
            **existing_schedule,
            **config.COMMUNITY_STATS_CELERYBEAT_SCHEDULE,
        }
        existing_aggregations = app.config.get("STATS_AGGREGATIONS", {})
        app.config["STATS_AGGREGATIONS"] = {
            **existing_aggregations,
            **config.COMMUNITY_STATS_AGGREGATIONS,
        }
        existing_queries = app.config.get("STATS_QUERIES", {})
        app.config["STATS_QUERIES"] = {
            **existing_queries,
            **config.COMMUNITY_STATS_QUERIES,
        }
        app.config["REQUESTS_EVENTS_SERVICE_COMPONENTS"] = [
            *app.config.get("REQUESTS_EVENTS_SERVICE_COMPONENTS", []),
            CommunityAcceptedEventComponent,
        ]
        existing_rdm_record_components = app.config.get(
            "RDM_RECORDS_SERVICE_COMPONENTS", []
        )
        app.logger.error(
            f"existing_rdm_record_components: {existing_rdm_record_components}"
        )
        app.config["RDM_RECORDS_SERVICE_COMPONENTS"] = [
            *existing_rdm_record_components,
            RecordCommunityEventComponent,
        ]
        existing_record_communities_components = app.config.get(
            "RDM_RECORD_COMMUNITIES_SERVICE_COMPONENTS", []
        )
        app.config["RDM_RECORD_COMMUNITIES_SERVICE_COMPONENTS"] = [
            *existing_record_communities_components,
            RecordCommunityEventTrackingComponent,
        ]


def finalize_app(app):
    """Finalize app."""
    _register_menus(app)
    _ensure_templates_registered(app)


def _register_menus(app):
    """Register menu."""
    # Check if menu is enabled
    if not app.config.get("STATS_DASHBOARD_MENU_ENABLED", True):
        return

    # Check for custom registration function
    custom_func = app.config.get("STATS_DASHBOARD_MENU_REGISTRATION_FUNCTION")
    if custom_func is not None:
        if callable(custom_func):
            custom_func(app)
        else:
            app.logger.warning(
                "STATS_DASHBOARD_MENU_REGISTRATION_FUNCTION is not callable, "
                "using default menu registration"
            )
            _register_default_menu(app)
    else:
        _register_default_menu(app)


def _register_default_menu(app):
    """Register the default stats menu item."""
    current_menu.submenu("main.stats").register(
        endpoint=app.config.get(
            "STATS_DASHBOARD_MENU_ENDPOINT",
            "invenio_stats_dashboard.global_stats_dashboard",
        ),
        text=app.config.get("STATS_DASHBOARD_MENU_TEXT", _("Stats")),
        order=app.config.get("STATS_DASHBOARD_MENU_ORDER", 1),
    )
