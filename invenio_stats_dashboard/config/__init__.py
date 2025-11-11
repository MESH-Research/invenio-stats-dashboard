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

import importlib

# Import all objects from config.py first (this directly imports the module file)
# This avoids the circular import that occurs with "from . import config"
# because "from .config import *" directly imports from the .config module file,
# whereas "from . import config" tries to resolve through the package namespace
from .config import *  # noqa: F403, F405, F401

# Get the config module object itself
# The wildcard import above already loaded it, so this just retrieves it
config = importlib.import_module(
    '.config', __package__ or __name__
)

__all__ = ['config']

for name in dir(config):
    if not name.startswith('_') and name not in __all__ and name.isupper():
        value = getattr(config, name)
        if not (isinstance(value, type) or callable(value)):
            __all__.append(name)
