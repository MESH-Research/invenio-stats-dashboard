# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Custom exceptions for Invenio Stats Dashboard."""


class DependencyError(Exception):
    """Exception raised when required dependencies are missing."""

    pass


class CommunityEventIndexingError(Exception):
    """Exception raised when community event indexing fails."""

    pass


class TaskLockAcquisitionError(Exception):
    """Exception raised when a distributed task lock cannot be acquired."""

    pass


class DeltaDataGapError(ValueError):
    """Exception raised when there's a gap in delta data for snapshot aggregation."""

    pass
