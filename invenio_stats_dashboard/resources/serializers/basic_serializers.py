# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Serializers for invenio-stats-dashboard content negotiation."""

import json
from typing import Any

from flask import Response, current_app


class StatsJSONSerializer:
    """JSON serializer for stats responses."""

    def serialize(self, data: dict | list | bytes, **kwargs) -> dict | list | Any:
        """Serialize data to JSON format.

        Args:
            data: The data to serialize (dict, list, or bytes)
            **kwargs: Additional keyword arguments

        Returns:
            Raw JSON-ready data (dict or list) ready to be dumped to JSON
        """
        if isinstance(data, bytes):
            try:
                json_data = json.loads(data.decode('utf-8'))
                return json_data
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                current_app.logger.warning(f"Failed to decode bytes data to JSON: {e}")
                return {"error": "Invalid JSON data"}

        return data