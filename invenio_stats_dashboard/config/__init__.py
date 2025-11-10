# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Configuration modules for invenio-stats-dashboard.

The config package exports:
1. The config module itself: `from .config import config`
2. All configuration constants (uppercase names, excluding types/functions)
3. Submodules remain separate and must be imported explicitly

This approach allows:
- from .config import config  # The module
- from .config import COMMUNITY_STATS_QUERIES  # Constants
- from .config.component_metrics import ...  # Submodules (explicit import)
"""

from . import config
from .config import *  # noqa: F403, F405, F401  # Import all objects from config.py

__all__ = ['config']

for name in dir(config):
    if not name.startswith('_') and name not in __all__ and name.isupper():
        value = getattr(config, name)
        if not (isinstance(value, type) or callable(value)):
            __all__.append(name)
