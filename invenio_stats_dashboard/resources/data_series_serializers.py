# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

# type: ignore
"""Enhanced serializers for data series with compression support."""

import gzip
import json
from typing import Union

from flask import Response

from .serializers import (
    StatsCSVSerializer,
    StatsExcelSerializer,
    StatsHTMLSerializer,
    StatsXMLSerializer,
)
from ..transformers.base import DataSeries


class CompressedStatsJSONSerializer:
    """Compressed JSON serializer for data series responses."""

    def serialize(self, data: Union[DataSeries, dict, list], **kwargs) -> Response:
        """Serialize data to compressed JSON format.

        Args:
            data: DataSeries object, dict, or list to serialize
            **kwargs: Additional keyword arguments

        Returns:
            Flask Response with compressed JSON content
        """
        # Convert DataSeries to dict if needed
        if isinstance(data, DataSeries):
            json_data = data.for_json()
        elif isinstance(data, dict):
            # Handle dict of DataSeries objects
            json_data = {}
            for key, value in data.items():
                if isinstance(value, DataSeries):
                    json_data[key] = value.for_json()
                else:
                    json_data[key] = value
        else:
            json_data = data

        # Serialize to JSON
        json_str = json.dumps(json_data, indent=2, default=str)

        # Compress the JSON
        compressed_data = gzip.compress(json_str.encode("utf-8"))
        return Response(
            compressed_data,
            mimetype="application/json",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Content-Encoding": "gzip",
                "Content-Disposition": "attachment; filename=stats.json.gz",
            },
        )


class DataSeriesCSVSerializer(StatsCSVSerializer):
    """CSV serializer for data series responses."""

    def serialize(self, data: Union[DataSeries, dict, list], **kwargs) -> Response:
        """Serialize data to CSV format.

        Args:
            data: DataSeries object, dict, or list to serialize
            **kwargs: Additional keyword arguments

        Returns:
            Flask Response with CSV content
        """
        # Convert DataSeries to list of data points
        if isinstance(data, DataSeries):
            csv_data = [dp.to_dict() for dp in data.data]
        elif isinstance(data, dict):
            # Handle dict of DataSeries objects
            csv_data = []
            for key, value in data.items():
                if isinstance(value, DataSeries):
                    for dp in value.data:
                        dp_dict = dict(dp.to_dict())  # Convert to regular dict
                        dp_dict["series_id"] = value.id
                        dp_dict["series_name"] = value.name
                        dp_dict["category"] = value.category
                        dp_dict["metric"] = value.metric
                        csv_data.append(dp_dict)
                else:
                    csv_data.append({key: value})
        else:
            csv_data = data

        return super().serialize(csv_data, **kwargs)


class DataSeriesExcelSerializer(StatsExcelSerializer):
    """Excel serializer for data series responses."""

    def serialize(self, data: Union[DataSeries, dict, list], **kwargs) -> Response:
        """Serialize data to Excel format.

        Args:
            data: DataSeries object, dict, or list to serialize
            **kwargs: Additional keyword arguments

        Returns:
            Flask Response with Excel content
        """
        # Convert DataSeries to dict format
        if isinstance(data, DataSeries):
            excel_data = {
                "series_info": {
                    "id": data.id,
                    "name": data.name,
                    "category": data.category,
                    "metric": data.metric,
                    "type": data.type,
                    "value_type": data.value_type,
                },
                "data_points": [dp.to_dict() for dp in data.data],
            }
        elif isinstance(data, dict):
            # Handle dict of DataSeries objects
            excel_data = {}
            for key, value in data.items():
                if isinstance(value, DataSeries):
                    excel_data[key] = {
                        "series_info": {
                            "id": value.id,
                            "name": value.name,
                            "category": value.category,
                            "metric": value.metric,
                            "type": value.type,
                            "value_type": value.value_type,
                        },
                        "data_points": [dp.to_dict() for dp in value.data],
                    }
                else:
                    excel_data[key] = value
        else:
            excel_data = data

        return super().serialize(excel_data, **kwargs)


class DataSeriesXMLSerializer(StatsXMLSerializer):
    """XML serializer for data series responses."""

    def serialize(self, data: Union[DataSeries, dict, list], **kwargs) -> Response:
        """Serialize data to XML format.

        Args:
            data: DataSeries object, dict, or list to serialize
            **kwargs: Additional keyword arguments

        Returns:
            Flask Response with XML content
        """
        # Convert DataSeries to dict format
        if isinstance(data, DataSeries):
            xml_data = data.for_json()
        elif isinstance(data, dict):
            # Handle dict of DataSeries objects
            xml_data = {}
            for key, value in data.items():
                if isinstance(value, DataSeries):
                    xml_data[key] = value.for_json()
                else:
                    xml_data[key] = value
        else:
            xml_data = data

        return super().serialize(xml_data, **kwargs)


class DataSeriesHTMLSerializer(StatsHTMLSerializer):
    """HTML serializer for data series responses."""

    def serialize(self, data: Union[DataSeries, dict, list], **kwargs) -> Response:
        """Serialize data to HTML format.

        Args:
            data: DataSeries object, dict, or list to serialize
            **kwargs: Additional keyword arguments

        Returns:
            Flask Response with HTML content
        """
        # Convert DataSeries to dict format
        if isinstance(data, DataSeries):
            html_data = data.for_json()
        elif isinstance(data, dict):
            # Handle dict of DataSeries objects
            html_data = {}
            for key, value in data.items():
                if isinstance(value, DataSeries):
                    html_data[key] = value.for_json()
                else:
                    html_data[key] = value
        else:
            html_data = data

        return super().serialize(html_data, **kwargs)
