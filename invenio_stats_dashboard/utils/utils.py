# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Utility functions for the stats dashboard."""


def get_subcount_field(config: dict, field_name: str, index: int = 0) -> str | None:
    """Get field value from subcount config using source_fields structure.

    Args:
        config: Subcount configuration dictionary
        field_name: Name of the field to extract (e.g., 'field', 'label_field')
        index: Index of the source_fields entry to use (default: 0)

    Returns:
        Field value or None if not found
    """
    source_fields = config.get("source_fields", [])
    if index < len(source_fields):
        result = source_fields[index].get(field_name)
        return result if isinstance(result, str) else None
    return None


def get_subcount_label_includes(config: dict, index: int = 0) -> list[str]:
    """Get label_source_includes from subcount config using source_fields structure.

    Args:
        config: Subcount configuration dictionary
        index: Index of the source_fields entry to use (default: 0)

    Returns:
        List of label source includes
    """
    source_fields = config.get("source_fields", [])
    if index < len(source_fields):
        result = source_fields[index].get("label_source_includes", [])
        return result if isinstance(result, list) else []
    return []


def get_subcount_combine_subfields(config: dict, index: int = 0) -> list[str]:
    """Get combine_subfields from subcount config using source_fields structure.

    Args:
        config: Subcount configuration dictionary
        index: Index of the source_fields entry to use (default: 0)

    Returns:
        List of combine subfields
    """
    source_fields = config.get("source_fields", [])
    if index < len(source_fields):
        result = source_fields[index].get("combine_subfields", [])
        return result if isinstance(result, list) else []
    return []


def format_bytes(bytes_value: int | None) -> str:
    """Format bytes into human readable format.

    Args:
        bytes_value: Size in bytes, or None

    Returns:
        Human-readable size string (e.g., "1.23 KB" or "unknown" if None)
    """
    if bytes_value is None:
        return "unknown"
    value = float(bytes_value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"


def format_age(age_seconds: int | None) -> str:
    """Format age in seconds into human readable format.

    Args:
        age_seconds: Age in seconds, or None

    Returns:
        Human-readable age string (e.g., "2h 30m" or "3d 5h" or "unknown" if None)
    """
    if age_seconds is None:
        return "unknown"
    if age_seconds < 0:
        return "unknown"

    # Convert to appropriate units
    if age_seconds < 60:
        return f"{age_seconds}s"
    elif age_seconds < 3600:
        minutes = age_seconds // 60
        seconds = age_seconds % 60
        if seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {seconds}s"
    elif age_seconds < 86400:  # Less than a day
        hours = age_seconds // 3600
        minutes = (age_seconds % 3600) // 60
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h {minutes}m"
    else:  # Days or more
        days = age_seconds // 86400
        hours = (age_seconds % 86400) // 3600
        if hours == 0:
            return f"{days}d"
        return f"{days}d {hours}h"
