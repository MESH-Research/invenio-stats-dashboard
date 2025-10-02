# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Wrapper functions for ContentNegotiatedMethodView serializers."""

from flask import Response, jsonify

from .basic_serializers import (
    StatsCSVSerializer,
    StatsExcelSerializer,
    StatsJSONSerializer,
    StatsXMLSerializer,
)
from .data_series_serializers import (
    BrotliStatsJSONSerializer,
    DataSeriesCSVSerializer,
    DataSeriesExcelSerializer,
    DataSeriesXMLSerializer,
    GzipStatsJSONSerializer,
)


# Basic serializer wrapper functions
def json_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for JSON serialization."""
    serializer = StatsJSONSerializer()
    json_data = serializer.serialize(data, **kwargs)
    response = jsonify(json_data)
    if headers:
        response.headers.update(headers)
    return response


def csv_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for CSV serialization."""
    serializer = StatsCSVSerializer()
    response = serializer.serialize(data, **kwargs)
    if headers:
        response.headers.update(headers)
    return response


def xml_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for XML serialization."""
    serializer = StatsXMLSerializer()
    response = serializer.serialize(data, **kwargs)
    if headers:
        response.headers.update(headers)
    return response


def excel_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Excel serialization."""
    serializer = StatsExcelSerializer()
    response = serializer.serialize(data, **kwargs)
    if headers:
        response.headers.update(headers)
    return response


# Data series serializer wrapper functions
def gzip_json_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Gzip JSON serialization."""
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
    """Wrapper function for Brotli JSON serialization."""
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
    """Wrapper function for Data Series CSV serialization."""
    serializer = DataSeriesCSVSerializer()
    compressed_data = serializer.serialize(data, **kwargs)
    response = Response(
        compressed_data,
        mimetype="application/gzip",
        headers={
            "Content-Type": "application/gzip",
            "Content-Disposition": "attachment; filename=stats.csv.tar.gz",
        },
    )
    if headers:
        response.headers.update(headers)
    return response


def data_series_xml_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Data Series XML serialization."""
    serializer = DataSeriesXMLSerializer()
    xml_string = serializer.serialize(data, **kwargs)
    response = Response(
        xml_string,
        mimetype="application/xml",
        headers={
            "Content-Type": "application/xml; charset=utf-8",
            "Content-Disposition": "attachment; filename=stats.xml",
        },
    )
    if headers:
        response.headers.update(headers)
    return response


def data_series_excel_serializer_func(data, code=200, headers=None, **kwargs):
    """Wrapper function for Data Series Excel serialization."""
    serializer = DataSeriesExcelSerializer()
    compressed_data = serializer.serialize(data, **kwargs)
    response = Response(
        compressed_data,
        mimetype="application/gzip",
        headers={
            "Content-Type": "application/gzip",
            "Content-Disposition": "attachment; filename=stats.xlsx.tar.gz",
        },
    )
    if headers:
        response.headers.update(headers)
    return response
