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

## Statistics

We want to show the following statistics:

- Number of records in collection
  - Total at a given point of time (time series for histogram)
- Number of new records added
  - Total during a given period (time series for histogram)
- Number of record views
  - Total at a given point of time (time series for histogram)
  - Total during a given period (time series for histogram)
- Number of file downloads
  - Total at a given point of time (time series for histogram)
  - Total during a given period (times series for histogram)
- Data traffic (i.e., download volume)
  - Total at a given point of time (time series for histogram)
  - Total during a given period (time series for histogram)
- Data volume in collection
  - Total at a given point of time (time series for histogram)
  - Total during a given period (time series for histogram)
- Number of uploaders
  - Total at a given point of time (time series for histogram)
  - Total during a given period (time series for histogram)
- Top records by views
  - During a given period
- Top records by downloads
  - During a given period
- Top records by data traffic
  - During a given period
- Top users by created records
- Top languages
  - During a given period
- Top visitor countries
  - During a given period
- Top referrers
  - During a given period
- Top access rights
  - During a given period
- Top record types
  - During a given period
- Top record licenses
  - During a given period
- Top funders for created records
- Top affiliations
- Top subject headings?
- Top communities?
- Top sub-communities?


All record statistics should be presentable either for individual versions or for parents (all versions at once).


## Development

```bash
# Install development dependencies
pip install -e ".[all]"

# Run tests
pytest
```