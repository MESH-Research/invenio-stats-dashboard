# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Content negotiation utilities for invenio-stats-dashboard."""

from importlib import import_module

from flask import Response, current_app, request

from .serializers import StatsJSONSerializer


class ContentNegotiationMixin:
    """Mixin class to add content negotiation support to query classes."""

    def _get_serializer_for_content_type(
        self, content_type: str, query_name: str | None = None
    ):
        """Get serializer instance for the given content type and query.

        Args:
            content_type: MIME type for the content
            query_name: Name of the query being executed (optional)

        Returns:
            Serializer instance or None if not found or not enabled for query
        """
        if not query_name:
            return None

        serializer_path = (
            current_app.config.get("STATS_SERIALIZERS", {})
            .get(content_type, {})
            .get("serializer")
        )
        if not serializer_path:
            return None

        try:
            module_path, class_name = serializer_path.rsplit(".", 1)
            module = import_module(module_path)
            serializer_class = getattr(module, class_name)
            return serializer_class()
        except (ImportError, AttributeError) as e:
            current_app.logger.warning(
                f"Failed to load serializer {serializer_path}: {e}"
            )
            return None

    def _get_available_content_types_for_query(
        self, query_name: str | None = None
    ) -> list[str]:
        """Get content types available for a query."""
        if not query_name:
            return list(current_app.config.get("STATS_SERIALIZERS", {}).keys())

        return [
            content_type
            for content_type, config in current_app.config.get(
                "STATS_SERIALIZERS", {}
            ).items()
            if query_name in config.get("enabled_for", [])
        ]

    def serialize_response(
        self,
        data: dict | list,
        query_name: str | None = None,
    ) -> Response | dict | list:
        """Serialize data using the appropriate serializer.

        Args:
            data: Data to serialize
            query_name: Name of the query being executed (optional)

        Returns:
            Flask Response object
        """
        content_type = self._get_preferred_content_type(query_name)

        if content_type is not None and query_name is not None:
            serializer = self._get_serializer_for_content_type(content_type, query_name)
            if serializer:
                return serializer.serialize(data)

        # Default to JSON if no specific serializer found
        return StatsJSONSerializer().serialize(data)

    def should_use_content_negotiation(self, query_name: str | None = None) -> bool:
        """Check if content negotiation should be used.

        Args:
            query_name: Name of the query being executed (optional)

        Returns:
            True if content negotiation should be used
        """
        available_serializers = current_app.config.get("STATS_SERIALIZERS", {})
        if not available_serializers:
            return False

        # Check for Accept header or compression preference
        accept_header = request.headers.get("Accept")
        accept_encoding = request.headers.get("Accept-Encoding", "")

        if not accept_header and "gzip" not in accept_encoding:
            return False

        if query_name:
            available_types = self._get_available_content_types_for_query(query_name)
            return len(available_types) > 0

        return True

    def _get_preferred_content_type(self, query_name: str | None = None) -> str | None:
        """Get the preferred content type based on Accept header and compression.

        Args:
            query_name: Name of the query being executed (optional)

        Returns:
            Preferred content type or None (None means use JSON default)
        """
        accept_header = request.headers.get("Accept", "")
        accept_encoding = request.headers.get("Accept-Encoding", "")

        # Check for compression preference first
        if "gzip" in accept_encoding:
            if "application/json" in accept_header or not accept_header:
                return "application/json+gzip"

        # Parse Accept header for content types
        if accept_header:
            # Look for acceptable content types in order of preference
            for content_type in accept_header.split(","):
                content_type = content_type.strip().split(";")[0]
                if query_name:
                    available_types = self._get_available_content_types_for_query(
                        query_name
                    )
                    if content_type in available_types:
                        return str(content_type)
                else:
                    if content_type in current_app.config.get("STATS_SERIALIZERS", {}):
                        return str(content_type)

        # If no Accept header or no acceptable types found, return JSON as default
        return "application/json"
