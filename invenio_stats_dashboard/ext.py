# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Invenio Stats Dashboard extension."""

from flask import Flask
from flask_menu import current_menu
from invenio_i18n import LazyString
from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.services.components import DefaultRecordsComponents
from invenio_search.proxies import current_search, current_search_client
from invenio_theme.proxies import current_theme_icons

from . import config
from .services.components import (
    CommunityAcceptedEventComponent,
    RecordCommunityEventComponent,
    RecordCommunityEventTrackingComponent,
)
from .services.service import CommunityStatsService
from .services.usage_reindexing import EventReindexingService


def _ensure_templates_registered(app: Flask) -> None:
    """Ensure that all invenio_stats_dashboard templates are registered.

    This function checks whether the templates for our custom aggregations are
    registered with OpenSearch. If they're not, it registers them with
    invenio_search and puts them to OpenSearch.

    This is necessary when the invenio_stats_dashboard package is added to an
    existing instance that already has a search domain set up, so the usual
    method for registering the invenio_stats templates doesn't work.
    """
    try:
        aggregations = config.COMMUNITY_STATS_AGGREGATIONS

        missing_templates = []
        templates = {}

        results = []
        for agg_config in aggregations.values():
            template_path = agg_config.get("templates")
            if template_path:
                try:
                    result = current_search.register_templates(template_path)
                    results.append(result)
                except Exception as e:
                    app.logger.warning(
                        f"Failed to register index template {template_path}: {e}"
                    )
                    missing_templates.append(template_path)

        for result in results:
            if isinstance(result, dict):
                for index_name, index_template in result.items():
                    templates[index_name] = index_template
            else:
                app.logger.warning(
                    f"Unexpected result type from register_templates: {type(result)}"
                )
                app.logger.warning(f"Result content: {result}")

        try:
            index_template_count = 0
            for index_name, index_template in templates.items():
                try:
                    current_search._put_template(
                        index_name,
                        index_template,
                        current_search_client.indices.put_index_template,
                        ignore=[400, 409],
                    )
                    index_template_count += 1
                except Exception as e:
                    app.logger.warning(f"Failed to put template {index_name}: {e}")

            if index_template_count == 0:
                app.logger.warning(
                    "No invenio_stats_dashboard index templates were put to OpenSearch"
                )

        except Exception as e:
            app.logger.error(f"Failed to put index templates to OpenSearch: {e}")

        if missing_templates:
            app.logger.warning(
                f"Failed to register {len(missing_templates)} index templates for "
                f"invenio_stats_dashboard: {missing_templates}"
            )

    except Exception as e:
        app.logger.error(
            f"Error during invenio_stats_dashboard index template check: {e}"
        )


class InvenioStatsDashboard:
    """Invenio Stats Dashboard extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)

        if app.config.get("COMMUNITY_STATS_ENABLED", True):
            self.service = CommunityStatsService(app)
            self.event_reindexing_service = EventReindexingService(app)
            app.extensions["invenio-stats-dashboard"] = self

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith("STATS_DASHBOARD_") or k.startswith("COMMUNITY_STATS_"):
                app.config.setdefault(k, getattr(config, k))

        if not app.config.get("COMMUNITY_STATS_ENABLED", True):
            app.logger.info(
                "Community stats dashboard is disabled. Skipping initialization."
            )
            return

        enabled_tasks = {}
        if app.config.get("COMMUNITY_STATS_SCHEDULED_AGG_TASKS_ENABLED", True):
            enabled_tasks = {**config.COMMUNITY_STATS_CELERYBEAT_AGG_SCHEDULE}
        else:
            app.logger.info(
                "Community stats scheduled aggregation tasks are disabled. "
                "Manual CLI operations are still possible."
            )

        if app.config.get("COMMUNITY_STATS_SCHEDULED_CACHE_TASKS_ENABLED", True):
            enabled_tasks = {
                **enabled_tasks,
                **config.COMMUNITY_STATS_CELERYBEAT_CACHE_SCHEDULE,
            }
        else:
            app.logger.info(
                "Community stats scheduled cache tasks are disabled. "
                "Manual CLI operations are still possible."
            )

        existing_schedule = app.config["CELERY_BEAT_SCHEDULE"]
        app.config["CELERY_BEAT_SCHEDULE"] = {
            **existing_schedule,
            **enabled_tasks,
        }

        existing_events = app.config.get("STATS_EVENTS", {})
        app.config["STATS_EVENTS"] = {
            **existing_events,
            **config.STATS_EVENTS,
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
            "RDM_RECORDS_SERVICE_COMPONENTS", [*DefaultRecordsComponents]
        )

        # Ensure the existing components list includes all defaults
        # This is a hack to fix component corruption during testing
        if app.config.get("TESTING", False):
            existing_rdm_record_components = self._ensure_rdm_service_components(
                app, existing_rdm_record_components
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

    def _ensure_rdm_service_components(self, app, components_list):
        """Ensure the components list includes all default RDM components.

        Args:
            app: Flask application
            components_list: List of existing components

        Returns:
            List of components with defaults ensured
        """
        try:
            component_names = [comp.__name__ for comp in components_list]
            default_component_names = [
                comp.__name__ for comp in DefaultRecordsComponents
            ]

            missing_components = [
                name for name in default_component_names if name not in component_names
            ]

            if missing_components:
                app.logger.warning(
                    f"Missing default RDM components: {missing_components}"
                )
                app.logger.warning("Adding default RDM components to the list")
                # Build corrected components list with defaults first
                corrected_components = DefaultRecordsComponents.copy()
                corrected_components.extend(components_list)
                return corrected_components
            else:
                # All defaults present, return original list
                return components_list

        except Exception as e:
            app.logger.error(f"Error ensuring RDM service components: {e}")
            # Fallback: return list with defaults
            corrected_components = DefaultRecordsComponents.copy()
            corrected_components.extend(components_list)
            return corrected_components


def finalize_app(app):
    """Finalize app."""
    _register_menus(app)
    _ensure_templates_registered(app)


def _register_menus(app):
    """Register menu."""
    # Check if stats and menu entry are enabled
    if not app.config.get("COMMUNITY_STATS_ENABLED", True) or not app.config.get(
        "STATS_DASHBOARD_MENU_ENABLED", True
    ):
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
        text=app.config.get(
            "STATS_DASHBOARD_MENU_TEXT",
            _(
                "%(icon)s Insights",
                icon=LazyString(
                    lambda: f'<i class="{current_theme_icons.chart_line}"></i>'
                ),
            ),
        ),
        order=app.config.get("STATS_DASHBOARD_MENU_ORDER", 1),
    )
