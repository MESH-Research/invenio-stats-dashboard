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
