# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Wrapper functions for ContentNegotiatedMethodView serializers."""

from flask import Response, jsonify

from .basic_serializers import (
    StatsJSONSerializer,
)
from .data_series_serializers import (  # type: ignore
    BrotliStatsJSONSerializer,  # type: ignore
    DataSeriesCSVSerializer,  # type: ignore
    DataSeriesExcelSerializer,  # type: ignore
    DataSeriesXMLSerializer,  # type: ignore
    GzipStatsJSONSerializer,  # type: ignore
)


# Basic serializer wrapper functions
def json_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for JSON serialization.

    Returns:
        Response: The Flask Response object for a regular
            JSON serialized response.
    """
    serializer = StatsJSONSerializer()
    json_data = serializer.serialize(data, **kwargs)
    response = jsonify(json_data)
    if headers:
        response.headers.update(headers)
    return response


# Data series serializer wrapper functions
def gzip_json_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Gzip JSON serialization.

    Returns:
        Response: The Flask Response object for a compressed
            JSON serialized response.
    """
    serializer = GzipStatsJSONSerializer()
    compressed_data = serializer.serialize(data, **kwargs)
    response = Response(
        compressed_data,
        mimetype="application/json",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Content-Encoding": "gzip",
            "Content-Disposition": "attachment; filename=stats.json.gz",
        },
    )
    if headers:
        response.headers.update(headers)
    return response


def brotli_json_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Brotli JSON serialization.

    Returns:
        Response: The Flask Response object for a compressed
            JSON serialized response.
    """
    serializer = BrotliStatsJSONSerializer()
    compressed_data = serializer.serialize(data, **kwargs)
    response = Response(
        compressed_data,
        mimetype="application/json",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Content-Encoding": "br",
            "Content-Disposition": "attachment; filename=stats.json.br",
        },
    )
    if headers:
        response.headers.update(headers)
    return response


def data_series_csv_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Data Series CSV serialization.

    Returns:
        Response: The Flask Response object for a csv serialized response.
    """
    serializer = DataSeriesCSVSerializer()
    compressed_data = serializer.serialize(data, **kwargs)

    # Generate proper filename with community ID if provided
    community_id = kwargs.get("community_id")
    if community_id:
        filename = f"data_series_csv_{community_id}.tar.gz"
    else:
        filename = "data_series_csv.tar.gz"

    response = Response(
        compressed_data,
        mimetype="application/gzip",
        headers={
            "Content-Type": "application/gzip",
            "Content-Encoding": "gzip",
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
    if headers:
        response.headers.update(headers)
    return response


def data_series_xml_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Data Series XML serialization.

    Returns:
        Response: The Falsk Response object for an xml serialized response.
    """
    serializer = DataSeriesXMLSerializer()
    xml_string = serializer.serialize(data, **kwargs)

    # Generate proper filename with community ID if provided
    community_id = kwargs.get("community_id")
    if community_id:
        filename = f"data_series_xml_{community_id}.xml"
    else:
        filename = "data_series_xml.xml"

    response = Response(
        xml_string,
        mimetype="application/xml",
    )
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    if headers:
        response.headers.update(headers)
    return response


def data_series_excel_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Data Series Excel serialization.

    Returns:
        Response: The Flask Response object for an Excel serialized response.
    """
    serializer = DataSeriesExcelSerializer()
    compressed_data = serializer.serialize(data, **kwargs)

    # Generate proper filename with community ID if provided
    community_id = kwargs.get("community_id")
    if community_id:
        filename = f"data_series_excel_{community_id}.tar.gz"
    else:
        filename = "data_series_excel.tar.gz"

    response = Response(
        compressed_data,
        mimetype="application/gzip",
        headers={
            "Content-Type": "application/gzip",
            "Content-Encoding": "gzip",
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
    if headers:
        response.headers.update(headers)
    return response
