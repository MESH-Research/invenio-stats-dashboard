# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Invenio Stats Dashboard views.

This module contains the views for the Invenio Stats Dashboard.
"""

from flask import (
    Blueprint,
    Flask,
    Response,
    current_app,
    render_template,
    request,
)
from invenio_communities.views.communities import HEADER_PERMISSIONS
from invenio_communities.views.decorators import pass_community
from invenio_records_resources.services.errors import PermissionDeniedError
from invenio_rest.views import ContentNegotiatedMethodView

from ..services.cached_response_service import CachedResponseService


def global_stats_dashboard():
    """Global stats dashboard view.
    
    Returns:
        str: Rendered HTML template for the global stats dashboard.
    """
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
            "use_test_data": current_app.config.get(
                "STATS_DASHBOARD_USE_TEST_DATA", True
            ),
            "ui_subcounts": current_app.config.get(
                "STATS_DASHBOARD_UI_SUBCOUNTS", {}
            ),
            "compress_json": current_app.config.get(
                "STATS_DASHBOARD_COMPRESS_JSON", True
            ),
            **current_app.config["STATS_DASHBOARD_UI_CONFIG"]["global"],
        },
    )


@pass_community(serialize=True)
def community_stats_dashboard(pid_value, community, community_ui):
    """Community stats dashboard view.
    
    Returns:
        str: Rendered HTML template for the community stats dashboard.
        
    Raises:
        PermissionDeniedError: If user lacks read permission for the community.
    """
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
            "use_test_data": current_app.config.get(
                "STATS_DASHBOARD_USE_TEST_DATA", True
            ),
            "ui_subcounts": current_app.config.get(
                "STATS_DASHBOARD_UI_SUBCOUNTS", {}
            ),
            "compress_json": current_app.config.get(
                "STATS_DASHBOARD_COMPRESS_JSON", True
            ),
            **current_app.config["STATS_DASHBOARD_UI_CONFIG"]["community"],
        },
        community=community_ui,
        permissions=permissions,
    )


class StatsDashboardAPIResource(ContentNegotiatedMethodView):
    """Custom stats dashboard API resource that bypasses invenio-stats middleware."""

    view_name = "stats_dashboard_api"

    def __init__(self, **kwargs):
        """Constructor."""
        serializers = current_app.config.get("COMMUNITY_STATS_SERIALIZERS", {})

        super().__init__(
            method_serializers={
                "POST": serializers,
            },
            default_method_media_type={
                "POST": "application/json",  # Default to plain JSON for testing
            },
            default_media_type="application/json",
            **kwargs,
        )

    def _build_json_response(self, results: dict[str, bytes]) -> bytes:
        """Build JSON response by concatenating raw JSON bytes.

        Use manual byte string concatenation to avoid double serialization
        of the JSON data.

        Args:
            results: Dictionary mapping query names to raw JSON bytes

        Returns:
            Complete JSON response bytes
        """
        json_parts = []
        for i, (query_name, raw_json_bytes) in enumerate(results.items()):
            if i > 0:
                json_parts.append(b",")
            json_parts.append(f'"{query_name}":'.encode())
            json_parts.append(raw_json_bytes)

        return b"{" + b"".join(json_parts) + b"}"

    def post(self, **kwargs):
        """Handle stats dashboard API requests with cache checking.
        
        Returns:
            Response: JSON response with stats data or error message.
        """
        try:
            request_data = request.get_json()
            if not request_data:
                return {"error": "No JSON data provided"}, 400

            configured_queries = current_app.config.get("COMMUNITY_STATS_QUERIES", {})
            allowed_params = [
                "community_id",
                "start_date",
                "end_date",
                "category",
                "metric",
                "date_basis",
            ]

            # Validate request parameters
            for query_name, query_data in request_data.items():
                if query_name not in configured_queries:
                    return {"error": f"Unknown query: {query_name}"}, 400

                query_params = query_data.get("params", {})
                if any([p for p in query_params.keys() if p not in allowed_params]):
                    return {
                        "error": (
                            f"Unknown parameter in request body for "
                            f"query {query_name}"
                        )
                    }, 400

            # Determine if we're requesting JSON (for special raw byte handling)
            accept_header = request.headers.get('Accept', 'application/json')
            is_json_request = 'application/json' in accept_header

            cache_service = CachedResponseService()

            results = {}

            for query_name, query_data in request_data.items():
                individual_request = {query_name: query_data}
                result = cache_service.get_or_create(
                    individual_request, as_json_bytes=is_json_request
                )
                results[query_name] = result

            # For JSON responses, handle raw bytes to avoid double serialization
            if is_json_request and all(
                isinstance(v, bytes) for v in results.values()
            ):
                final_json = self._build_json_response(results)
                return Response(final_json, mimetype=accept_header)
            
            # For all other cases, return the data and let the parent class's
            # dispatch_request method handle content negotiation and serialization
            return results

        except Exception as e:
            current_app.logger.error(f"Stats API error: {str(e)}")
            return {"error": str(e)}, 500


def create_blueprint(app: Flask) -> Blueprint:
    """Create the Invenio-Stats-Dashboard blueprint.
    
    Returns:
        Blueprint: The configured stats dashboard blueprint.
    """
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


def create_api_blueprint(app: Flask) -> Blueprint:
    """Create the Invenio-Stats-Dashboard api blueprint.

    This supplements the regular stats api endpoint to allow
    for content negotiation and serialized responses.
    
    Returns:
        Blueprint: The configured stats dashboard API blueprint.
    """
    api_routes = app.config["STATS_DASHBOARD_API_ROUTES"]

    api_blueprint = Blueprint(
        "invenio_stats_dashboard_api",
        __name__,
        template_folder="../templates",
    )

    stats_api_view = StatsDashboardAPIResource.as_view("stats_dashboard_api")
    api_blueprint.add_url_rule(
        api_routes["stats_series"],
        view_func=stats_api_view,
        methods=["POST"],
        strict_slashes=False,
    )

    return api_blueprint
