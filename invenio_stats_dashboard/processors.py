# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Data series transformers for converting indexed documents to chart-ready data."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from flask import current_app


class DataPoint:
    """Represents a single data point in a time series."""

    def __init__(self, date: Union[str, datetime], value: Union[int, float],
                 value_type: str = 'number'):
        """Initialize a data point.

        Args:
            date: Date string (YYYY-MM-DD) or datetime object
            value: Numeric value for this data point
            value_type: Type of value ('number', 'filesize', etc.)
        """
        if isinstance(date, datetime):
            self.date = date.strftime('%Y-%m-%d')
        else:
            self.date = date
        self.value = value
        self.value_type = value_type

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching JavaScript output."""
        return {
            'value': [self.date, self.value],
            'readableDate': self._format_readable_date(),
            'valueType': self.value_type
        }

    def _format_readable_date(self) -> str:
        """Format date for human readability."""
        try:
            dt = datetime.strptime(self.date, '%Y-%m-%d')
            return dt.strftime('%b %d, %Y')
        except ValueError:
            return self.date


class DataSeries:
    """Represents a complete data series for charting."""

    def __init__(self, series_id: str, name: str, data_points: List[DataPoint],
                 chart_type: str = 'line', value_type: str = 'number'):
        """Initialize a data series.

        Args:
            series_id: Unique identifier for the series
            name: Display name for the series
            data_points: List of data points in the series
            chart_type: Type of chart ('line', 'bar', etc.)
            value_type: Type of values in the series
        """
        self.id = series_id
        self.name = name
        self.data = data_points
        self.type = chart_type
        self.value_type = value_type

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching JavaScript output."""
        return {
            'id': self.id,
            'name': self.name,
            'data': [dp.to_dict() for dp in self.data],
            'type': self.type,
            'valueType': self.value_type
        }


class BaseDataSeriesTransformer(ABC):
    """Base class for transforming indexed documents into data series."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the transformer.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.subcount_configs = current_app.config.get(
            'COMMUNITY_STATS_SUBCOUNT_CONFIGS', {})
        self.ui_subcounts = current_app.config.get(
            'STATS_DASHBOARD_UI_SUBCOUNTS', {})

    @abstractmethod
    def transform(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform documents into data series.

        Args:
            documents: List of indexed documents to transform

        Returns:
            Dictionary containing transformed data series
        """
        pass

    def create_data_point(self, date: Union[str, datetime],
                         value: Union[int, float],
                         value_type: str = 'number') -> DataPoint:
        """Create a data point object.

        Args:
            date: Date string or datetime object
            value: Numeric value
            value_type: Type of value

        Returns:
            DataPoint object
        """
        return DataPoint(date, value, value_type)

    def create_global_series(self, data_points: List[DataPoint],
                           chart_type: str = 'line',
                           value_type: str = 'number') -> DataSeries:
        """Create a global data series.

        Args:
            data_points: List of data points
            chart_type: Type of chart
            value_type: Type of values

        Returns:
            DataSeries object with id "global"
        """
        return DataSeries("global", "Global", data_points, chart_type,
                         value_type)

    def create_data_series_array(self, series_names: List[str],
                               data_points_array: List[Dict[str, Any]] = None,
                               chart_type: str = 'line',
                               value_type: str = 'number') -> List[DataSeries]:
        """Create an array of data series from named properties.

        Args:
            series_names: List of property names to extract as separate series
            data_points_array: Array of data points with named properties
            chart_type: Chart type for all series
            value_type: Value type for all series

        Returns:
            List of DataSeries objects
        """
        if data_points_array is None:
            data_points_array = []

        series_array = []
        for name in series_names:
            series = DataSeries(name, name, [], chart_type, value_type)
            series_array.append(series)

        for point_obj in data_points_array:
            date = point_obj.get('date')
            if not date:
                continue

            for name in series_names:
                if name in point_obj:
                    series = next((s for s in series_array if s.name == name),
                                None)
                    if series:
                        data_point = self.create_data_point(
                            date, point_obj[name], value_type)
                        series.data.append(data_point)

        return series_array

    def create_data_series_from_items(self, subcount_items: List[Dict[str, Any]],
                                    data_points_array: List[Dict[str, Any]] = None,
                                    chart_type: str = 'line',
                                    value_type: str = 'number',
                                    localization_map: Dict[str, str] = None
                                    ) -> List[DataSeries]:
        """Create data series from subcount items.

        Args:
            subcount_items: List of subcount items with id and optional label
            data_points_array: Array of data points mapping subcount id to value
            chart_type: Chart type for all series
            value_type: Value type for all series
            localization_map: Map of subcount id to localized label

        Returns:
            List of DataSeries objects
        """
        if data_points_array is None:
            data_points_array = []
        if localization_map is None:
            localization_map = {}

        series_array = []
        for item in subcount_items:
            series_id = item.get('id', '')
            series_name = localization_map.get(series_id, series_id)
            series = DataSeries(series_id, series_name, [], chart_type,
                              value_type)
            series_array.append(series)

        for point_obj in data_points_array:
            date = point_obj.get('date')
            if not date:
                continue

            for series in series_array:
                if series.id in point_obj:
                    data_point = self.create_data_point(
                        date, point_obj[series.id], value_type)
                    series.data.append(data_point)

        return series_array

    def create_localization_map(self, documents: List[Dict[str, Any]]
                              ) -> Dict[str, str]:
        """Create a localization map from documents.

        Args:
            documents: List of documents containing subcount data

        Returns:
            Dictionary mapping subcount id to localized label
        """
        localization_map = {}

        # Collect all unique subcount items from all documents
        all_subcount_items = {}

        for doc in documents:
            subcounts = doc.get('subcounts', {})
            for subcount_type, subcount_series in subcounts.items():
                if isinstance(subcount_series, list):
                    if subcount_type not in all_subcount_items:
                        all_subcount_items[subcount_type] = []

                    for item in subcount_series:
                        if not any(existing.get('id') == item.get('id')
                                 for existing in all_subcount_items[subcount_type]):
                            all_subcount_items[subcount_type].append(item)

        # Process each subcount category to create the localization map
        for category_key, subcount_items in all_subcount_items.items():
            for item in subcount_items:
                item_id = item.get('id')
                item_label = item.get('label')

                if item_id and item_label:
                    # Handle both string and object labels
                    if isinstance(item_label, str):
                        localized_label = item_label
                    elif isinstance(item_label, dict):
                        # Use English as fallback, or first available language
                        localized_label = item_label.get(
                            'en', next(iter(item_label.values()), ''))
                    else:
                        localized_label = str(item_label)

                    localization_map[item_id] = localized_label

        return localization_map

    def to_json(self, data: Dict[str, Any]) -> str:
        """Convert data to JSON string matching JavaScript output format.

        Args:
            data: Transformed data dictionary

        Returns:
            JSON string
        """
        def convert_to_json_serializable(obj):
            """Recursively convert objects to JSON-serializable format."""
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif isinstance(obj, dict):
                return {k: convert_to_json_serializable(v)
                       for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_json_serializable(item) for item in obj]
            else:
                return obj

        return json.dumps(convert_to_json_serializable(data), indent=2)


class RecordDeltaDataSeriesTransformer(BaseDataSeriesTransformer):
    """Transformer for record delta aggregation documents."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the record delta transformer."""
        super().__init__(config)
        self.subcount_types = {
            'resource_types': 'resourceTypes',
            'access_statuses': 'accessStatuses',
            'languages': 'languages',
            'affiliations_creators': 'affiliations',
            'affiliations_contributors': 'affiliations',
            'funders': 'funders',
            'subjects': 'subjects',
            'publishers': 'publishers',
            'periodicals': 'periodicals',
            'rights': 'rights',
            'file_types': 'fileTypes'
        }

    def transform(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform record delta documents into data series.

        Args:
            documents: List of record delta aggregation documents

        Returns:
            Dictionary containing transformed data series
        """
        delta_data = self._initialize_delta_data_structure()

        if not documents:
            return delta_data

        # Create localization map from all documents
        localization_map = self.create_localization_map(documents)

        for doc in documents:
            date = doc.get('period_start', '').split('T')[0]
            if not date:
                continue

            # Process global data
            self._process_global_data(doc, date, delta_data)

            # Process file presence data
            self._process_file_presence_data(doc, date, delta_data)

            # Process subcount data
            self._process_subcount_data(doc, date, delta_data,
                                      localization_map)

        # Convert data points to series
        self._convert_to_series(delta_data, localization_map)

        return delta_data

    def _initialize_delta_data_structure(self) -> Dict[str, Any]:
        """Initialize the delta data structure."""
        return {
            'global': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'filePresence': {
                'records': [],
                'parents': []
            },
            'accessStatuses': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'languages': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'affiliations': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'funders': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'subjects': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'publishers': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'periodicals': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'rights': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'fileTypes': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'resourceTypes': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
        }

    def _get_net_count(self, item: Dict[str, Any]) -> int:
        """Calculate net count change for a subcount item."""
        if 'added' in item and 'removed' in item:
            added = (item['added'].get('metadata_only', 0) +
                    item['added'].get('with_files', 0))
            removed = (item['removed'].get('metadata_only', 0) +
                      item['removed'].get('with_files', 0))
            return added - removed
        return 0

    def _get_net_file_count(self, item: Dict[str, Any]) -> int:
        """Calculate net file count change for a subcount item."""
        if 'added' in item and 'removed' in item:
            return (item['added'].get('file_count', 0) -
                   item['removed'].get('file_count', 0))
        elif 'files' in item:
            files = item['files']
            return ((files.get('added', {}).get('file_count', 0)) -
                   (files.get('removed', {}).get('file_count', 0)))
        return 0

    def _get_net_data_volume(self, item: Dict[str, Any]) -> int:
        """Calculate net data volume change for a subcount item."""
        if 'added' in item and 'removed' in item:
            return (item['added'].get('data_volume', 0) -
                   item['removed'].get('data_volume', 0))
        elif 'files' in item:
            files = item['files']
            return ((files.get('added', {}).get('data_volume', 0)) -
                   (files.get('removed', {}).get('data_volume', 0)))
        return 0

    def _process_global_data(self, doc: Dict[str, Any], date: str,
                           delta_data: Dict[str, Any]):
        """Process global data points."""
        # Records
        records_net = self._get_net_count(doc.get('records', {}))
        delta_data['global']['records'].append(
            self.create_data_point(date, records_net)
        )

        # Parents
        parents_net = self._get_net_count(doc.get('parents', {}))
        delta_data['global']['parents'].append(
            self.create_data_point(date, parents_net)
        )

        # Uploaders
        uploaders = doc.get('uploaders', 0)
        delta_data['global']['uploaders'].append(
            self.create_data_point(date, uploaders)
        )

        # File count
        file_count_net = self._get_net_file_count(doc.get('files', {}))
        delta_data['global']['fileCount'].append(
            self.create_data_point(date, file_count_net)
        )

        # Data volume
        data_volume_net = self._get_net_data_volume(doc.get('files', {}))
        delta_data['global']['dataVolume'].append(
            self.create_data_point(date, data_volume_net, 'filesize')
        )

    def _process_file_presence_data(self, doc: Dict[str, Any], date: str,
                                  delta_data: Dict[str, Any]):
        """Process file presence data points."""
        for key in ['records', 'parents']:
            data_point = {'date': date}

            # Calculate net change for delta data
            added_data = doc.get(key, {}).get('added', {})
            removed_data = doc.get(key, {}).get('removed', {})

            data_point['withFiles'] = (added_data.get('with_files', 0) -
                                     removed_data.get('with_files', 0))
            data_point['metadataOnly'] = (added_data.get('metadata_only', 0) -
                                        removed_data.get('metadata_only', 0))

            delta_data['filePresence'][key].append(data_point)

    def _process_subcount_data(self, doc: Dict[str, Any], date: str,
                             delta_data: Dict[str, Any],
                             localization_map: Dict[str, str]):
        """Process subcount data points."""
        subcounts = doc.get('subcounts', {})

        for subcount_type, target_key in self.subcount_types.items():
            subcount_series = subcounts.get(subcount_type, [])
            if not subcount_series:
                continue

            # Initialize data structures if needed
            if f'{target_key}DataPoints' not in delta_data:
                delta_data[f'{target_key}DataPoints'] = {
                    'records': [], 'parents': [], 'uploaders': [],
                    'fileCount': [], 'dataVolume': []
                }
                delta_data[f'{target_key}Items'] = []

            for item in subcount_series:
                # Store item for later series creation
                if not any(existing.get('id') == item.get('id')
                          for existing in delta_data[f'{target_key}Items']):
                    delta_data[f'{target_key}Items'].append(item)

                # Process each metric type
                metric_types = ['records', 'parents', 'uploaders',
                              'fileCount', 'dataVolume']
                for metric_type in metric_types:
                    value = 0

                    if metric_type == 'records':
                        value = self._get_net_count(item.get('records', item))
                    elif metric_type == 'parents':
                        value = self._get_net_count(item.get('parents', item))
                    elif metric_type == 'uploaders':
                        value = item.get('uploaders', 0)
                    elif metric_type == 'fileCount':
                        value = self._get_net_file_count(item.get('files', item))
                    elif metric_type == 'dataVolume':
                        value = self._get_net_data_volume(item.get('files', item))

                    # Find or create data point for this date
                    data_points = delta_data[f'{target_key}DataPoints'][metric_type]
                    existing_data_point = next(
                        (dp for dp in data_points if dp.get('date') == date), None
                    )
                    if not existing_data_point:
                        existing_data_point = {'date': date}
                        data_points.append(existing_data_point)

                    existing_data_point[item['id']] = value

    def _convert_to_series(self, delta_data: Dict[str, Any],
                         localization_map: Dict[str, str]):
        """Convert data points to series."""
        # Convert global data points to series
        delta_data['global']['records'] = [self.create_global_series(
            delta_data['global']['records'], 'line', 'number')]
        delta_data['global']['parents'] = [self.create_global_series(
            delta_data['global']['parents'], 'line', 'number')]
        delta_data['global']['uploaders'] = [self.create_global_series(
            delta_data['global']['uploaders'], 'line', 'number')]
        delta_data['global']['fileCount'] = [self.create_global_series(
            delta_data['global']['fileCount'], 'line', 'number')]
        delta_data['global']['dataVolume'] = [self.create_global_series(
            delta_data['global']['dataVolume'], 'line', 'filesize')]

        # Create file presence series
        for metric_type in ['records', 'parents']:
            data_points = delta_data['filePresence'][metric_type]
            value_type = 'filesize' if metric_type == 'dataVolume' else 'number'
            delta_data['filePresence'][metric_type] = self.create_data_series_array(
                ['withFiles', 'metadataOnly'], data_points, 'line', value_type)

        # Create subcount series
        for subcount_type, target_key in self.subcount_types.items():
            if (f'{target_key}Items' in delta_data and
                    f'{target_key}DataPoints' in delta_data):
                metric_types = ['records', 'parents', 'uploaders',
                              'fileCount', 'dataVolume']
                for metric_type in metric_types:
                    value_type = 'filesize' if metric_type == 'dataVolume' else 'number'
                    delta_data[target_key][metric_type] = self.create_data_series_from_items(
                        delta_data[f'{target_key}Items'],
                        delta_data[f'{target_key}DataPoints'][metric_type],
                        'line', value_type, localization_map
                    )

                # Clean up temporary data
                del delta_data[f'{target_key}Items']
                del delta_data[f'{target_key}DataPoints']


class RecordSnapshotDataSeriesTransformer(BaseDataSeriesTransformer):
    """Transformer for record snapshot aggregation documents."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the record snapshot transformer."""
        super().__init__(config)
        self.subcount_types = {
            'resource_types': 'resourceTypes',
            'access_statuses': 'accessStatuses',
            'languages': 'languages',
            'affiliations_creator': 'affiliations',
            'affiliations_contributor': 'affiliations',
            'funders': 'funders',
            'subjects': 'subjects',
            'publishers': 'publishers',
            'periodicals': 'periodicals',
            'rights': 'rights',
            'file_types': 'fileTypes'
        }

    def transform(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Transform record snapshot documents into data series.

        Args:
            documents: List of record snapshot aggregation documents

        Returns:
            Dictionary containing transformed data series
        """
        snapshot_data = self._initialize_snapshot_data_structure()

        if not documents:
            return snapshot_data

        # Create localization map from all documents
        localization_map = self.create_localization_map(documents)

        for doc in documents:
            date = doc.get('snapshot_date', '').split('T')[0]
            if not date:
                continue

            # Process global data
            self._process_global_data(doc, date, snapshot_data)

            # Process file presence data
            self._process_file_presence_data(doc, date, snapshot_data)

            # Process subcount data
            self._process_subcount_data(doc, date, snapshot_data,
                                      localization_map)

        # Convert data points to series
        self._convert_to_series(snapshot_data, localization_map)

        return snapshot_data

    def _initialize_snapshot_data_structure(self) -> Dict[str, Any]:
        """Initialize the snapshot data structure."""
        return {
            'global': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'filePresence': {
                'records': [],
                'parents': []
            },
            'accessStatuses': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'languages': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'affiliations': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'funders': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'subjects': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'publishers': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'periodicals': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'rights': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'fileTypes': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
            'resourceTypes': {
                'records': [],
                'parents': [],
                'uploaders': [],
                'fileCount': [],
                'dataVolume': [],
            },
        }

    def _get_total_count(self, item: Dict[str, Any]) -> int:
        """Calculate total count for a record item."""
        if not item:
            return 0
        return (item.get('metadata_only', 0) + item.get('with_files', 0))

    def _get_total_file_count(self, item: Dict[str, Any]) -> int:
        """Extract total file count from a record item."""
        if not item:
            return 0
        return item.get('file_count', 0)

    def _get_total_data_volume(self, item: Dict[str, Any]) -> int:
        """Extract total data volume from a record item."""
        if not item:
            return 0
        return item.get('data_volume', 0)

    def _process_global_data(self, doc: Dict[str, Any], date: str,
                           snapshot_data: Dict[str, Any]):
        """Process global data points."""
        # Records
        total_records = self._get_total_count(doc.get('total_records', {}))
        snapshot_data['global']['records'].append(
            self.create_data_point(date, total_records)
        )

        # Parents
        total_parents = self._get_total_count(doc.get('total_parents', {}))
        snapshot_data['global']['parents'].append(
            self.create_data_point(date, total_parents)
        )

        # Uploaders
        total_uploaders = doc.get('total_uploaders', 0)
        snapshot_data['global']['uploaders'].append(
            self.create_data_point(date, total_uploaders)
        )

        # File count
        total_file_count = self._get_total_file_count(doc.get('total_files', {}))
        snapshot_data['global']['fileCount'].append(
            self.create_data_point(date, total_file_count)
        )

        # Data volume
        total_data_volume = self._get_total_data_volume(doc.get('total_files', {}))
        snapshot_data['global']['dataVolume'].append(
            self.create_data_point(date, total_data_volume, 'filesize')
        )

    def _process_file_presence_data(self, doc: Dict[str, Any], date: str,
                                  snapshot_data: Dict[str, Any]):
        """Process file presence data points."""
        for key in ['records', 'parents']:
            data_point = {'date': date}
            total_data = doc.get(f'total_{key}', {})

            data_point['withFiles'] = total_data.get('with_files', 0)
            data_point['metadataOnly'] = total_data.get('metadata_only', 0)

            snapshot_data['filePresence'][key].append(data_point)

    def _process_subcount_data(self, doc: Dict[str, Any], date: str,
                             snapshot_data: Dict[str, Any],
                             localization_map: Dict[str, str]):
        """Process subcount data points."""
        subcounts = doc.get('subcounts', {})

        for subcount_type, target_key in self.subcount_types.items():
            subcount_series = subcounts.get(subcount_type, [])
            if not subcount_series:
                continue

            # Initialize data structures if needed
            if f'{target_key}DataPoints' not in snapshot_data:
                snapshot_data[f'{target_key}DataPoints'] = {
                    'records': [], 'parents': [], 'uploaders': [],
                    'fileCount': [], 'dataVolume': []
                }
                snapshot_data[f'{target_key}Items'] = []

            for item in subcount_series:
                # Store item for later series creation
                if not any(existing.get('id') == item.get('id')
                          for existing in snapshot_data[f'{target_key}Items']):
                    snapshot_data[f'{target_key}Items'].append(item)

                # Process each metric type
                metric_types = ['records', 'parents', 'uploaders',
                              'fileCount', 'dataVolume']
                for metric_type in metric_types:
                    value = 0

                    if metric_type == 'records':
                        value = self._get_total_count(item.get('records', item))
                    elif metric_type == 'parents':
                        value = self._get_total_count(item.get('parents', item))
                    elif metric_type == 'uploaders':
                        value = item.get('total_uploaders', 0)
                    elif metric_type == 'fileCount':
                        value = self._get_total_file_count(item.get('files', item))
                    elif metric_type == 'dataVolume':
                        value = self._get_total_data_volume(item.get('files', item))

                    # Find or create data point for this date
                    data_points = snapshot_data[f'{target_key}DataPoints'][metric_type]
                    existing_data_point = next(
                        (dp for dp in data_points if dp.get('date') == date), None
                    )
                    if not existing_data_point:
                        existing_data_point = {'date': date}
                        data_points.append(existing_data_point)

                    existing_data_point[item['id']] = value

    def _convert_to_series(self, snapshot_data: Dict[str, Any],
                         localization_map: Dict[str, str]):
        """Convert data points to series."""
        # Convert global data points to series
        snapshot_data['global']['records'] = [self.create_global_series(
            snapshot_data['global']['records'], 'bar', 'number')]
        snapshot_data['global']['parents'] = [self.create_global_series(
            snapshot_data['global']['parents'], 'bar', 'number')]
        snapshot_data['global']['uploaders'] = [self.create_global_series(
            snapshot_data['global']['uploaders'], 'bar', 'number')]
        snapshot_data['global']['fileCount'] = [self.create_global_series(
            snapshot_data['global']['fileCount'], 'bar', 'number')]
        snapshot_data['global']['dataVolume'] = [self.create_global_series(
            snapshot_data['global']['dataVolume'], 'bar', 'filesize')]

        # Create file presence series
        for metric_type in ['records', 'parents']:
            data_points = snapshot_data['filePresence'][metric_type]
            value_type = 'filesize' if metric_type == 'dataVolume' else 'number'
            snapshot_data['filePresence'][metric_type] = self.create_data_series_array(
                ['withFiles', 'metadataOnly'], data_points, 'line', value_type)

        # Create subcount series
        for subcount_type, target_key in self.subcount_types.items():
            if (f'{target_key}Items' in snapshot_data and
                    f'{target_key}DataPoints' in snapshot_data):
                metric_types = ['records', 'parents', 'uploaders',
                              'fileCount', 'dataVolume']
                for metric_type in metric_types:
                    value_type = 'filesize' if metric_type == 'dataVolume' else 'number'
                    snapshot_data[target_key][metric_type] = self.create_data_series_from_items(
                        snapshot_data[f'{target_key}Items'],
                        snapshot_data[f'{target_key}DataPoints'][metric_type],
                        'line', value_type, localization_map
                    )

                # Clean up temporary data
                del snapshot_data[f'{target_key}Items']
                del snapshot_data[f'{target_key}DataPoints']


# Factory function for creating transformers
def create_transformer(transformer_type: str,
                      config: Optional[Dict[str, Any]] = None
                      ) -> BaseDataSeriesTransformer:
    """Create a transformer instance based on type.

    Args:
        transformer_type: Type of transformer ('record_delta', 'record_snapshot',
                         'usage_delta', 'usage_snapshot')
        config: Optional configuration dictionary

    Returns:
        Appropriate transformer instance

    Raises:
        ValueError: If transformer_type is not recognized
    """
    transformers = {
        'record_delta': RecordDeltaDataSeriesTransformer,
        'record_snapshot': RecordSnapshotDataSeriesTransformer,
        'usage_delta': UsageDeltaDataSeriesTransformer,
        'usage_snapshot': UsageSnapshotDataSeriesTransformer,
    }

    if transformer_type not in transformers:
        raise ValueError(f"Unknown transformer type: {transformer_type}")

    return transformers[transformer_type](config)