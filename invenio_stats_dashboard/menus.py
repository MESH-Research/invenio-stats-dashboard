# Part of Invenio Stats Dashboard
# Copyright (C) 2023-2026, MESH Research
#
# Invenio Stats Dashboard is free software; you can redistribute and/or
# modify it under the terms of the MIT License; see LICENSE file for more details.

"""Menu item registration helpers for Invenio Stats Dashboard."""

from flask import current_app, request
from flask_menu import current_menu
from invenio_i18n import LazyString
from invenio_i18n import lazy_gettext as _
from invenio_theme.proxies import current_theme_icons


def register_menus(app):
    """Register menu."""
    # Check if stats and menu entry are enabled (unchanged from original)
    if not app.config.get("COMMUNITY_STATS_ENABLED", True):
        return

    # Check for custom registration functions
    if app.config.get("STATS_DASHBOARD_MENU_ENABLED", True):
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

    if app.config.get("STATS_DASHBOARD_COMMUNITY_MENU_ENABLED", True):
        custom_func = app.config.get(
            "STATS_DASHBOARD_COMMUNITY_MENU_REGISTRATION_FUNCTION"
        )
        if custom_func is not None:
            if callable(custom_func):
                custom_func(app)
            else:
                app.logger.warning(
                    "STATS_DASHBOARD_COMMUNITY_MENU_REGISTRATION_FUNCTION is not callable, "
                    "using default community menu registration"
                )
                _register_default_community_menu(app)
        else:
            _register_default_community_menu(app)


def _register_default_menu(app):
    """Register the default stats menu item (main nav)."""
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


def _community_dashboard_enabled() -> bool:
    """Check whether the community's dashboard is enabled."""
    if not hasattr(request, "community"):
        return False

    if not current_app.config.get("COMMUNITY_STATS_ENABLED", True):
        return False

    if not current_app.config.get("STATS_DASHBOARD_ENABLED_COMMUNITY", False):
        return False

    if not current_app.config.get("STATS_DASHBOARD_COMMUNITY_OPT_IN", True):
        return True

    custom_fields = request.community.get("custom_fields") or {}
    return bool(custom_fields.get("stats:dashboard_enabled"))


def _register_default_community_menu(app):
    """Register the Statistics tab on the community details header menu."""
    current_menu.submenu("communities").submenu("stats").register(
        endpoint=app.config.get(
            "STATS_DASHBOARD_COMMUNITY_MENU_ENDPOINT",
            "invenio_stats_dashboard.community_stats_dashboard",
        ),
        text=app.config.get(
            "STATS_DASHBOARD_COMMUNITY_MENU_TEXT",
            _("Statistics"),
        ),
        order=app.config.get("STATS_DASHBOARD_COMMUNITY_MENU_ORDER", 35),
        # expected_args: URL args the endpoint needs; used by flask-menu to build
        # item.url (e.g. url_for(endpoint, pid_value=...)) when rendering the menu.
        expected_args=["pid_value"],
        icon="chart line",
        # permissions: key in the community details permissions dict; item is shown
        # only if permissions[permissions] is truthy.
        permissions="can_read",
        visible_when=_community_dashboard_enabled,
    )
