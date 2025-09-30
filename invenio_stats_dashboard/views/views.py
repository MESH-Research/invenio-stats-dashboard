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
    abort,
    current_app,
    render_template,
    request,
)
from invenio_communities.views.communities import HEADER_PERMISSIONS
from invenio_communities.views.decorators import pass_community
from invenio_records_resources.services.errors import PermissionDeniedError
from invenio_rest.views import ContentNegotiatedMethodView

from ..resources.cache_utils import StatsCache


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
            "use_test_data": current_app.config.get(
                "STATS_DASHBOARD_USE_TEST_DATA", True
            ),
            "ui_subcounts": current_app.config.get("STATS_DASHBOARD_UI_SUBCOUNTS", {}),
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
            "use_test_data": current_app.config.get(
                "STATS_DASHBOARD_USE_TEST_DATA", True
            ),
            "ui_subcounts": current_app.config.get("STATS_DASHBOARD_UI_SUBCOUNTS", {}),
            **current_app.config["STATS_DASHBOARD_UI_CONFIG"]["community"],
        },
        community=community_ui,
        permissions=permissions,
    )


class StatsDashboardAPIResource(ContentNegotiatedMethodView):
    """Custom stats dashboard API resource that bypasses invenio-stats middleware."""

    view_name = "stats_dashboard_api"

    def _check_cache(self, query_name: str, query_params: dict) -> Response | None:
        """Check cache for the given query parameters.

        Args:
            query_name: Name of the query
            query_params: Query parameters dictionary

        Returns:
            Cached Response object or None if not found
        """
        serializers, default_media_type = self.get_method_serializers(
            request.method
        )
        serializer = self.match_serializers(serializers, default_media_type)

        content_type = None
        for ct, ser in serializers.items():
            if ser == serializer:
                content_type = ct
                break

        if content_type is None:
            return None

        cache = StatsCache()
        cache_params = self._prepare_cache_params(
            query_name, query_params, content_type
        )
        cached_data = cache.get_cached_data(**cache_params)

        if cached_data is not None:
            # Return Response object to bypass make_response()

            # Compressed data needs to be returned with encoding headers
            if content_type == "application/json+br":
                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Encoding": "br",
                    "X-Cache": "HIT",
                }
                response = Response(
                    cached_data,
                    mimetype="application/json",
                    headers=headers,
                )
                return response
            elif content_type == "application/json+gzip":
                headers = {
                    "Content-Type": "application/json; charset=utf-8",
                    "Content-Encoding": "gzip",
                    "X-Cache": "HIT",
                }
                response = Response(
                    cached_data,
                    mimetype="application/json",
                    headers=headers,
                )
                return response
            else:
                # For other content types, use the original content type
                headers = {
                    "Content-Type": f"{content_type}; charset=utf-8",
                    "X-Cache": "HIT",
                }
                response = Response(
                    cached_data,
                    mimetype=content_type,
                    headers=headers,
                )
                return response

        return None

    def _prepare_cache_params(
        self, query_name: str, query_params: dict, content_type: str
    ) -> dict:
        """Prepare cache parameters from query_params with defaults.

        Args:
            query_name: Name of the query
            query_params: Query parameters dictionary
            content_type: Content type for caching

        Returns:
            Dictionary of cache parameters
        """
        return {
            'stat_name': query_name,
            'content_type': content_type,
            'community_id': query_params.get('community_id', 'global'),
            'start_date': query_params.get('start_date', ''),
            'end_date': query_params.get('end_date', ''),
            'date_basis': query_params.get('date_basis', 'added'),
        }

    def __init__(self, **kwargs):
        """Constructor."""
        serializers = current_app.config.get("COMMUNITY_STATS_SERIALIZERS", {})

        super().__init__(
            serializers=serializers,
            default_method_media_type={
                "POST": "application/json",  # Default to plain JSON for testing
            },
            default_media_type="application/json",
            **kwargs,
        )

    def post(self, **kwargs):
        """Handle stats dashboard API requests with cache checking."""
        try:
            request_data = request.get_json()
            if not request_data:
                return {"error": "No JSON data provided"}, 400

            query_name = list(request_data.keys())[0]
            query_params = request_data[query_name].get("params", {})

            configured_queries = current_app.config.get("COMMUNITY_STATS_QUERIES", {})
            allowed_params = [
                "community_id",
                "start_date",
                "end_date",
                "category",
                "metric",
                "date_basis",
            ]

            if query_name not in configured_queries:
                return {"error": f"Unknown query: {query_name}"}, 400

            if any([p for p in query_params.keys() if p not in allowed_params]):
                return {"error": "Unknown parameter in request body"}

            # Check cache first - return early if hit
            cached_response = self._check_cache(query_name, query_params)
            if cached_response is not None:
                return cached_response

            # If not cached, execute query
            query_config = configured_queries[query_name]
            query_class = query_config["cls"]
            query_index = query_config["params"]["index"]

            query_instance = query_class(name=query_name, index=query_index)
            result = query_instance.run(**{
                k: v
                for k, v in query_params.items()
                if k
                in [
                    "community_id",
                    "start_date",
                    "end_date",
                    "category",
                    "metric",
                    "date_basis",
                ]
            })

            return {query_name: result}

        except Exception as e:
            current_app.logger.error(f"Stats API error: {str(e)}")
            return {"error": str(e)}, 500

    def make_response(self, *args, **kwargs):
        """Override to add caching after content negotiation and serialization."""
        # Get the determined serializer and content type
        serializers, default_media_type = self.get_method_serializers(request.method)
        serializer = self.match_serializers(serializers, default_media_type)

        content_type = None
        for ct, ser in serializers.items():
            if ser == serializer:
                content_type = ct
                break

        if serializer is None:
            abort(406)
        response = serializer(*args, **kwargs)

        # Cache the final serialized/compressed response
        try:
            request_data = request.get_json() or {}
            query_name = list(request_data.keys())[0] if request_data else "unknown"
            query_params = request_data.get(query_name, {}).get("params", {})

            if content_type is not None:
                cache = StatsCache()
                cache_params = self._prepare_cache_params(
                    query_name, query_params, content_type
                )

                cache.set_cached_data(
                    data=response.get_data(),
                    timeout=None,
                    **cache_params
                )
        except Exception as e:
            # Don't fail the request if caching fails
            current_app.logger.warning(f"Cache write error: {e}")

        return response


def create_blueprint(app: Flask) -> Blueprint:
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


def create_api_blueprint(app: Flask) -> Blueprint:
    """Create the Invenio-Stats-Dashboard api blueprint.

    This supplements the regular stats api endpoint to allow
    for content negotiation and serialized responses.
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
