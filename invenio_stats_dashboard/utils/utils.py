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
