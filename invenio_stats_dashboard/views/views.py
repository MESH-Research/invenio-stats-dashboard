# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Invenio Stats Dashboard views.

This module contains the views for the Invenio Stats Dashboard.
"""

import json

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
from ..resources.serializers.basic_serializers import StatsJSONSerializer


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
            "compress_json": current_app.config.get("STATS_DASHBOARD_COMPRESS_JSON", True),
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
            "compress_json": current_app.config.get("STATS_DASHBOARD_COMPRESS_JSON", True),
            **current_app.config["STATS_DASHBOARD_UI_CONFIG"]["community"],
        },
        community=community_ui,
        permissions=permissions,
    )


class StatsDashboardAPIResource(ContentNegotiatedMethodView):
    """Custom stats dashboard API resource that bypasses invenio-stats middleware."""

    view_name = "stats_dashboard_api"

    def _get_cached_data(self, query_name: str, query_params: dict) -> bytes | None:
        """Get cached data for the given query parameters.

        Args:
            query_name: Name of the query
            query_params: Query parameters dictionary

        Returns:
            Cached data bytes or None if not found
        """
        cache = StatsCache()
        cache_params = self._prepare_cache_params(
            query_name, query_params, "application/json"
        )
        return cache.get_cached_data(**cache_params)

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

            configured_queries = current_app.config.get("COMMUNITY_STATS_QUERIES", {})
            allowed_params = [
                "community_id",
                "start_date",
                "end_date",
                "category",
                "metric",
                "date_basis",
            ]

            # Use parent class content negotiation to determine content type
            serializers, default_media_type = self.get_method_serializers(request.method)
            serializer = self.match_serializers(serializers, default_media_type)

            if serializer is None:
                abort(406)

            # Get the actual content type that will be used
            content_type = getattr(serializer, 'media_type', default_media_type)

            # Check for cached entire response first
            cache = StatsCache()
            cached_response = cache.get_cached_response(
                content_type=content_type,
                request_data=request_data
            )

            if cached_response is not None:
                current_app.logger.info(f"=== CACHE HIT (ENTIRE RESPONSE) ===")
                current_app.logger.info(f"Content type: {content_type}")

                # For JSON content types, return cached bytes directly
                if content_type.startswith('application/json'):
                    return Response(
                        cached_response,
                        mimetype=content_type,
                        headers={"X-Cache": "HIT"}
                    )
                else:
                    # For other content types, decode and let serializer handle it
                    json_string = cached_response.decode('utf-8')
                    results = json.loads(json_string)
                    return results

            # Cache miss - build results dictionary
            current_app.logger.info(f"=== CACHE MISS (ENTIRE RESPONSE) ===")
            current_app.logger.info(f"Content type: {content_type}")

            results = {}
            for query_name, query_data in request_data.items():
                query_params = query_data.get("params", {})

                if query_name not in configured_queries:
                    return {"error": f"Unknown query: {query_name}"}, 400

                if any([p for p in query_params.keys() if p not in allowed_params]):
                    return {
                        "error": (
                            f"Unknown parameter in request body for query {query_name}"
                        )
                    }

                query_config = configured_queries[query_name]
                query_class = query_config["cls"]
                query_index = query_config["params"]["index"]

                query_instance = query_class(name=query_name, index=query_index)
                raw_json = query_instance.run(**{
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

                results[query_name] = raw_json

            # Cache the entire response
            json_data = json.dumps(results)
            timeout = current_app.config.get("STATS_CACHE_DEFAULT_TIMEOUT", None)
            success = cache.set_cached_response(
                content_type=content_type,
                request_data=request_data,
                response_data=json_data,
                timeout=timeout
            )
            current_app.logger.info(f"=== CACHE WRITE (ENTIRE RESPONSE) ===")
            current_app.logger.info(f"Content type: {content_type}")
            current_app.logger.info(f"Cache write success: {success}")

            # Debug: Show what keys are in Redis after this write
            all_keys = cache.list_cache_keys()
            current_app.logger.info(f"Total keys in Redis: {len(all_keys)}")
            for key in all_keys[:5]:  # Show first 5 stats keys
                current_app.logger.info(f"  Key: {key}")

            return results

        except Exception as e:
            current_app.logger.error(f"Stats API error: {str(e)}")
            return {"error": str(e)}, 500



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
