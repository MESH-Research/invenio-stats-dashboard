# Invenio Stats Dashboard

Invenio module that provides a stats dashboard component.

## Installation

```bash
pip install invenio-stats-dashboard
```

## Usage

The module provides a Jinja2 template that can be included in other templates:

```html
{%- extends "invenio_theme/page.html" %}
{%- import "invenio_stats_dashboard/stats_dashboard.html" as stats_dashboard %}

{%- block page_body %}
  {{ stats_dashboard.stats_dashboard() }}
{%- endblock %}
```

## Development

```bash
# Install development dependencies
pip install -e ".[all]"

# Run tests
pytest
```