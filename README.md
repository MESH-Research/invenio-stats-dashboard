# Invenio Stats Dashboard

Invenio module that provides a stats dashboard component.

## Installation

```bash
pip install invenio-stats-dashboard
```

## Usage

The module provides:

### Blueprints and routes

The module provides a blueprint `invenio_stats_dashboard.blueprint` that is registered with the following routes:

- `/stats` - the global dashboard.
- `/communities/<community_id>/stats` - the community dashboard.

These default routes are set via the `STATS_DASHBOARD_ROUTES` configuration variable and can be overridden.

### Jinja2 templates

#### Template macro

a Jinja2 template macro that can be included in other templates to display an embedded dashboard view:

```html
{%- extends "invenio_theme/page.html" %}
{%- import "invenio_stats_dashboard/stats_dashboard.html" as stats_dashboard %}

{%- block page_body %}
  {{ stats_dashboard.stats_dashboard() }}
{%- endblock %}
```

The macro takes the following parameters:

- `dashboard_config`: The configuration for the dashboard.
- `community`: The community to display the dashboard for (if `dashboard_type` is `community`). [Optional. Defaults to `None`].

#### Global dashboard template

A Jinja2 template for the global dashboard, registered as a top-level page template at the global stats dashboard route (`/stats` by default).

#### Community dashboard template

A Jinja2 template for the community dashboard page content, intended to be used as a sub-page of the community details page. This is registered with the community stats dashboard route (`/communities/<community_id>/stats` by default).

To implement this in your community details page, you can add a menu tab to the community details page template linking to this template route.

## Configuration

### Layout and components

The layout and components for the dashboard are configured via the `STATS_DASHBOARD_LAYOUT` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community`) to layout configurations. Each layout configuration is a dictionary that maps dashboard sections to a list of components to display in that section. Rows can be specified to group components together, and component widths can be specified with a "width" key.

For example, the default global layout configuration is:

```python
STATS_DASHBOARD_LAYOUT = {
    "global": {
        "tabs": [
            {
                "name": "content",
                "label": "Content",
                "rows": [
                    {
                        "name": "date-range-selector",
                        "components": [{"component": "DateRangeSelector", "width": 16}],
                    },
                    {
                        "name": "single-stats",
                        "components": [
                            {"component": "SingleStatRecordCount", "width": 3},
                            {"component": "SingleStatUploaders", "width": 3},
                            {"component": "SingleStatDataVolume", "width": 3},
                        ],
                    },
                    {
                        "name": "charts",
                        "components": [
                            {"component": "StatsChart", "width": 8},
                        ],
                    },
                    {
                        "name": "tables",
                        "components": [
                            {"component": "ResourceTypesTable", "width": 8},
                            {"component": "AccessRightsTable", "width": 8},
                            {"component": "LicensesTable", "width": 8},
                            {"component": "AffiliationsTable", "width": 8},
                        ],
                    },
                ],
            },
        ],
    },
}
```
If no layout configuration is provided for a dashboard type, the default "global" layout configuration will be used.

Any additional key/value pairs in the dictionary for a component will be passed to the component class as additional props. This allows for some customization of the component without having to subclass and override the component class.

The component labels used for the layout configuration are defined in the `components_map.js` file, where they are mapped to the component classes.

### Routes

The routes for the dashboard are defined by the `STATS_DASHBOARD_ROUTES` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community`) to route strings.

For example, the default routes are:

```python
STATS_DASHBOARD_ROUTES = {
    "global": "/stats",
    "community": "/communities/<community_id>/stats",
}
```

### Templates

The templates for the dashboard are defined by the `STATS_DASHBOARD_TEMPLATES` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community`) to template strings.

For example, the default templates are:

```python
STATS_DASHBOARD_TEMPLATES = {
    "macro": "invenio_stats_dashboard/macros/stats_dashboard_macro.html",
    "global": "invenio_stats_dashboard/stats_dashboard.html",
    "community": "invenio_stats_dashboard/community_stats_dashboard.html",
}
```

### UI Configuration

The UI configuration for the dashboard is defined by the `STATS_DASHBOARD_UI_CONFIG` configuration variable. This is a dictionary that maps dashboard types (currently `global` and `community`) to a dictionary of configuration options.

For example, the default UI configuration is:

```python
STATS_DASHBOARD_CONFIG = {
    "global": {
        "title": "Statistics Dashboard",
        "description": "This is the global stats dashboard.",
        "maxHistoryYears": 15,
        "show_title": True,
        "show_description": False,
    },
    "community": {
        "title": "Community Statistics Dashboard",
        "description": "This is the community stats dashboard.",
        "maxHistoryYears": 15,
        "show_title": True,
        "show_description": False,
    },
}
```

#### Title and description display

The title and description display in different places for the global and community dashboards. For the global dashboard, the title and description are displayed in the page subheader, while for the community dashboard they display at the top of the dashboard sidebar.

The `show_title` and `show_description` options can be used to control whether the title and description are displayed for the global and community dashboards.

## Statistics

We want to show the following statistics:

- Number of records in collection
  - Cumulative total at a given point of time (time series for histogram)
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

Time series data is very expensive to compute for large collections or for an entire instance. This cost is magnified if we want to cross-reference multiple time-series. So we pre-generate aggregated daily totals in search indices. One document is generated for each community for each day. If an instance has 10000 communities, this means 10000 documents per day. If we want to store 10 years of data, this means 10000 * 365 * 10 = 36_500_000 documents. To ensure the indices remain a manageable size (even for very large instances), we use separate annual indices. These are then linked by a common alias to facilitate easy searching across all years.

** visit counts for community landing page **

## Search indices for statistics

**Assume that STATS_REGISTER_INDEX_TEMPLATES is set to True.**

### stats-community-contents-snapshot

```json
{
  "timestamp": "2025-01-01",
  "community_id": "123",
  "period_start": "2025-01-01",
  "period_end": "2025-01-01",
  "record_count": 100,
  "parent_count": 10,
  "uploaders": 10,
  "subcounts": {
    "by_resource_type": [
      {
        "id": "textDocument-journalArticle",
        "label": {"en": "Journal Article"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "by_access_right": [
      {
        "id": "open",
        "label": {"en": "Open Access"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "by_language": [
      {
        "id": "en",
        "label": {"en": "English"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "top_affiliations": [
      {
        "id": "University of California, Berkeley",
        "label": {"en": "University of California, Berkeley"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "top_funders": [
      {
        "id": "National Science Foundation",
        "label": {"en": "National Science Foundation"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "top_subjects": [
      {
        "id": "123",
        "label": {"en": "Subject 1"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "top_publishers": [
      {
        "id": "University of California Press",
        "label": {"en": "University of California Press"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "top_periodicals": [
      {
        "id": "123",
        "label": {"en": "Periodical 1"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
  },
}
```

### stats-community-contents-delta

```json
{
  "timestamp": "2025-01-01",
  "community_id": "123",
  "records_added": 100,
  "records_removed": 10,
  "parents_added": 10,
  "parents_removed": 10,
  "uploaders": 10,
  "subcounts": {
    "by_resource_type": [
      {
        id: "textDocument-journalArticle",
        records_added: 100,
        records_removed: 10,
        parents_added: 10,
        parents_removed: 10,
      },
    ],
    "by_access_right": [
      {
        id: "open",
        label: {"en": "Open Access"},
        records_added: 100,
        records_removed: 10,
        parents_added: 10,
        parents_removed: 10,
      },
    ],
    "by_language": [
      {
        id: "en",
        label: {"en": "English"},
        records_added: 100,
        records_removed: 10,
        parents_added: 10,
        parents_removed: 10,
      },
    ],
    "by_affiliation": [
      {
        id: "University of California, Berkeley",
        records_added: 100,
        records_removed: 10,
        parents_added: 10,
        parents_removed: 10,
      },
    ],
    "by_funder": [
      {
        id: "National Science Foundation",
        records_added: 100,
        records_removed: 10,
        parents_added: 10,
        parents_removed: 10,
      },
    ],
    "by_subject": [
      {
        "id": "123",
        "label": {"en": "Subject 1"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "by_publisher": [
      {
        "id": "123",
        "label": {"en": "Publisher 1"},
        "record_count": 100,
        "parent_count": 10,
      },
    ],
    "by_periodical": [
      {
        "id": "123",
        "label": {"en": "Periodical 1"},
        "record_count": 100,
        "parent_count": 10,
      },
    ]
  },
],
},
}
```

- stats_community_record_usage
    - timestamp
    - community_id
    - period_record_views
    - cumulative_record_views
    - record_views
    - parent_views
    - record_views_to_date
    - parent_views_to_date
    - record_downloads
    - record_downloads_to_date
    - parent_downloads
    - parent_downloads_to_date
    - downloaded_data_volume
    - downloaded_data_volume_to_date
    - parent_downloaded_data_volume
    - parent_downloaded_data_volume_to_date
    - subcounts for
        - metadata.resource_type.id
        - metadata.access.???
        - metadata.rights.id
        - metadata.languages.id
        - country
        - referrer
        - metadata.creators.[n].affiliations[n].name
        - metadata.contributors.[n].affiliations[n].name
        - metadata.funding.funder.id
        - metadata.publisher
        - metadata.subjects[n].id
        - imprint:imprint.place
        - journal:journal.title
        - code:programmingLanguage[n]
        - code:developmentStatus
        - kcr:ai_usage.ai_used
        - kcr:commons_domain


## Development

```bash
# Install development dependencies
pip install -e ".[all]"

# Run tests
pytest
```