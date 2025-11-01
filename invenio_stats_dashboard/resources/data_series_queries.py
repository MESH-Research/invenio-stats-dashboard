# Part of the Invenio-Stats-Dashboard extension for InvenioRDM
# Copyright (C) 2025 Mesh Research
#
# Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Data series API query classes for invenio-stats-dashboard."""

import gc

import arrow
import orjson
import psutil
from flask import Response, current_app
from invenio_access.permissions import system_identity
from invenio_communities.proxies import current_communities
from invenio_stats.queries import Query
from opensearchpy import OpenSearch
from opensearchpy.helpers.query import Q
from opensearchpy.helpers.search import Search

from ..transformers.base import DataSeriesSet
from ..transformers.record_deltas import RecordDeltaDataSeriesSet
from ..transformers.record_snapshots import RecordSnapshotDataSeriesSet
from ..transformers.types import DataSeriesDict
from ..transformers.usage_deltas import UsageDeltaDataSeriesSet
from ..transformers.usage_snapshots import UsageSnapshotDataSeriesSet


class DataSeriesMemoryEstimator:
    """Estimate memory usage for data series query processing.
    
    Estimates memory consumption of:
    - Current page of query results (temporary, cleared each iteration)
    - Growing data series objects (DataSeriesArray with DataPoint accumulation)
    - Cached built result dictionary
    
    Caches estimation results to avoid recalculation on each page.
    """

    def __init__(
        self,
        series_count: int,
        initial_page_size: int,
        total_count: int | None = None,
        sample_doc_bytes: int | None = None,
    ) -> None:
        """Initialize estimator, reading all stable configuration from config.
        
        Args:
            series_count: Number of series arrays for this query.
            initial_page_size: Initial page size for pagination.
            total_count: Total number of documents in the query (for estimating
                total series growth). If None, will estimate conservatively.
            sample_doc_bytes: Measured bytes from a sample document. If provided,
                uses this instead of config default for more accurate estimates.
        """
        cfg = current_app.config
        
        self.k_page_overhead = float(
            cfg.get("STATS_DATA_SERIES_PAGE_OVERHEAD", 0.85)
        )
        self.k_series_overhead = float(
            cfg.get("STATS_DATA_SERIES_SERIES_OVERHEAD", 1.5)
        )
        self.safety_factor = float(
            cfg.get("STATS_DATA_SERIES_MEM_SAFETY_FACTOR", 1.2)
        )
        self.inmemory_factor = float(
            cfg.get("STATS_DATA_SERIES_INMEMORY_MULTIPLIER", 4.0)
        )
        
        # Estimated sizes for components
        self.bytes_per_datapoint = int(
            cfg.get("STATS_DATA_SERIES_BYTES_PER_DATAPOINT", 256)
        )
        self.avg_doc_bytes = int(
            cfg.get("STATS_DATA_SERIES_AVG_DOC_BYTES", 2048)
        )
        
        # Page size limits
        self.page_size_min = int(cfg.get("STATS_DATA_SERIES_PAGE_SIZE_MIN", 50))
        self.page_size_max = int(cfg.get("STATS_DATA_SERIES_PAGE_SIZE_MAX", 365))
        
        # ===== SECTION 2: Set up memory budget =====
        # Calculate how much memory we're allowed to use
        
        self.mem_budget_bytes = cfg.get("STATS_DATA_SERIES_MEM_BUDGET_BYTES")
        self.mem_high_water_percent = float(
            cfg.get("STATS_DATA_SERIES_MEM_HIGH_WATER_PERCENT", 0.75)
        )
        
        self.proc = psutil.Process()
        
        try:
            total_mem = psutil.virtual_memory().total
        except Exception:
            total_mem = 0
        
        if isinstance(self.mem_budget_bytes, int) and self.mem_budget_bytes > 0:
            self.budget_bytes = int(self.mem_budget_bytes)
        elif total_mem:
            self.budget_bytes = int(total_mem * self.mem_high_water_percent)
        else:
            self.budget_bytes = 0
        
        # ===== SECTION 3: Store query-specific parameters =====
        self.series_count = series_count
        self.days_processed: int = 0
        self.total_count: int | None = total_count
        
        # ===== SECTION 4: Pre-calculate multipliers =====
        # These are calculated once and reused for fast runtime calculations
        
        # Initial estimate for series growth per day (re-estimated after first page)
        self.series_bytes_per_day = int(
            series_count
            * self.bytes_per_datapoint
            * self.k_series_overhead
            * self.inmemory_factor
        )
        
        # ===== SECTION 5: Capture initial state =====
        # Capture RSS before any processing to measure actual growth later
        self.initial_rss: int = self.get_current_rss()
        # Set on first iteration, cleared after re-estimation
        self.rss_with_page: int | None = None
        
        # ===== SECTION 6: Initialize runtime state =====
        # Initial estimates for page memory (re-estimated after first page)
        self.current_page_size = initial_page_size
        # Initial estimate for bytes per document
        # Use sample if provided, otherwise fall back to config default
        # Note: sample_doc_bytes is serialized JSON bytes (from orjson), so we multiply
        # by inmemory_factor to approximate in-memory Python object size (similar to
        # usage_snapshot_aggs). avg_doc_bytes from config is treated as serialized too.
        base_doc_bytes = (
            sample_doc_bytes if sample_doc_bytes is not None else self.avg_doc_bytes
        )
        self.bytes_per_doc = int(
            base_doc_bytes * self.k_page_overhead * self.inmemory_factor
        )
        # Initial estimate for full page
        self.per_page_bytes = initial_page_size * self.bytes_per_doc
        
        # ===== SECTION 7: Pre-flight adjustment =====
        # Adjust initial page size if we're already close to budget
        if self.budget_bytes > 0:
            adjusted = self.adjust_page_size()
            if adjusted < initial_page_size:
                current_app.logger.info(
                    f"Pre-flight memory estimate: reducing initial page size from "
                    f"{initial_page_size} to {adjusted} "
                    f"(RSS: {self.initial_rss}, budget: {self.budget_bytes} bytes)"
                )

    def capture_page_rss(self) -> None:
        """Capture RSS while page is in memory (before cleanup)."""
        try:
            self.rss_with_page = self.get_current_rss()
        except Exception:
            self.rss_with_page = None
    
    def re_estimate_after_first_page(self, days_processed: int) -> None:
        """Re-estimate bytes_per_doc and series_bytes_per_day after first page."""
        if (
            self.initial_rss <= 0
            or self.rss_with_page is None
            or days_processed <= 0
        ):
            return
        
        try:
            rss_without_page = self.get_current_rss()
            page_bytes = self.rss_with_page - rss_without_page
            series_bytes = rss_without_page - self.initial_rss
            
            series_bytes_per_doc = None
            if series_bytes > 0:
                series_bytes_per_doc = int(series_bytes / days_processed)
                self.series_bytes_per_day = max(
                    self.series_bytes_per_day, series_bytes_per_doc
                )
            
            if page_bytes > 0 and self.current_page_size > 0:
                self.bytes_per_doc = int(page_bytes / self.current_page_size)
                self.per_page_bytes = int(self.current_page_size * self.bytes_per_doc)
            
            # Clear rss_with_page to indicate re-estimation is done
            self.rss_with_page = None
            
            current_app.logger.info(
                f"Re-estimated: series_bytes_per_day={self.series_bytes_per_day} "
                f"(measured: {series_bytes_per_doc or 'N/A'}, "
                f"days: {days_processed}, page_bytes={page_bytes})"
            )
        except Exception as e:
            current_app.logger.warning(f"Re-estimate failed: {e}")
    
    def update_page_size(self, days_processed: int) -> int:
        """Update days processed, re-estimate if needed, and adjust page size.
        
        Args:
            days_processed: Actual number of days processed.
        
        Returns:
            int: The adjusted page size (possibly unchanged).
        """
        self.days_processed = days_processed
        
        # Re-estimate after first page if we have measurements
        if self.rss_with_page is not None:
            self.re_estimate_after_first_page(days_processed)
        
        old_page_size = self.get_current_page_size()
        new_page_size = self.adjust_page_size()
        
        if new_page_size < old_page_size and self.budget_bytes > 0:
            try:
                rss = self.get_current_rss()
            except Exception as e:
                rss = 0
                current_app.logger.error(
                    f"Error getting RSS memory usage: {e}"
                )
            
            current_app.logger.warning(
                f"Reducing page size from {old_page_size} to {new_page_size} "
                f"(RSS: {rss}, budget: {self.budget_bytes} bytes)"
            )
        
        return new_page_size

    def get_current_rss(self) -> int:
        """Get current RSS memory usage.
        
        Returns:
            int: Current RSS in bytes, or 0 if unavailable.
        """
        try:
            return self.proc.memory_info().rss if self.proc else 0  # type: ignore[union-attr]
        except Exception:
            return 0

    def get_current_page_size(self) -> int:
        """Get the current page size.
        
        Returns:
            int: The current page size.
        """
        return self.current_page_size
    
    def adjust_page_size(self, current_used_bytes: int | None = None) -> int:
        """Adjust page size to fit within memory headroom.

        If we're over budget, reduces page size proportionally using two scaling
        methods and takes the more conservative result to ensure we stay under budget.
        Uses pre-calculated multipliers for minimal computation.

        Args:
            current_used_bytes: Current process memory usage in bytes.
                If None, fetches from proc.

        Returns:
            int: The adjusted page size (possibly unchanged).
        """
        if self.budget_bytes <= 0:
            return self.current_page_size
        
        if current_used_bytes is None:
            current_used_bytes = self.get_current_rss()
        
        # Calculate additional memory needed for the NEXT page:
        # 1. Next page of documents (temporary, will be cleared after processing)
        # 2. All remaining series growth (from next page onwards)
        # Note: days_processed already includes the current page, so remaining_docs
        # excludes the current page, which is correct since it's already processed.
        if self.total_count is not None:
            # Calculate remaining documents after current page
            remaining_docs = max(0, self.total_count - self.days_processed)
            remaining_series_growth = self.series_bytes_per_day * remaining_docs
        else:
            # Conservative estimate: assume we'll accumulate at least as much more
            # as we already have
            remaining_series_growth = (
                self.series_bytes_per_day
                * (self.days_processed + self.current_page_size)
            )
        
        # Peak memory = current + next page (temp) + remaining series growth (permanent)
        additional_memory_needed = (
            self.per_page_bytes + remaining_series_growth
        )
        
        # Peak memory if we process next page = current used + additional memory needed
        peak_memory = current_used_bytes + additional_memory_needed
        
        # If we fit within budget, no adjustment needed
        if peak_memory <= self.budget_bytes:
            return self.current_page_size

        # We're over budget - need to reduce page size
        # Calculate how much memory we have available for additional growth
        free_bytes = max(1, self.budget_bytes - current_used_bytes)
        
        # Edge case: invalid calculation
        if additional_memory_needed <= 0:
            # Just clamp to valid range
            return max(
                self.page_size_min,
                min(self.current_page_size, self.page_size_max)
            )
        
        # Calculate two scaling factors and use the more conservative (smaller) one:
        # Pattern matches usage_snapshot_aggs for consistency
        
        # 1. Linear scaling: stricter cap to ensure we definitely fit
        #    Clamp to minimum first (matches usage_snapshot_aggs pattern)
        #    This gives: new_size ≈ current_size * (free / needed)
        #    Example: if free is 25% of needed, scale by 0.25
        linear_cap = max(
            self.page_size_min,
            int(self.current_page_size * (free_bytes / float(additional_memory_needed)))
        )
        
        # 2. Square root scaling: gentler reduction, avoids over-shrinking
        #    This gives: new_size ≈ current_size * sqrt(free / needed)
        #    Example: if free is 25% of needed, scale by sqrt(0.25) = 0.5
        sqrt_scale = (free_bytes / float(additional_memory_needed)) ** 0.5
        sqrt_proposed = int(self.current_page_size * sqrt_scale)
        
        # Take the more conservative (smaller) value, clamped to valid range
        adjusted = max(
            self.page_size_min,
            min(sqrt_proposed, self.page_size_max, linear_cap)
        )
        
        # Update per-page bytes estimate only if page size actually changed
        if adjusted != self.current_page_size:
            self.current_page_size = adjusted
            self.per_page_bytes = int(adjusted * self.bytes_per_doc)
        
        return adjusted


class DataSeriesQueryBase(Query):
    """Base class for data series API queries."""

    date_field: str  # Type annotation for child classes
    transformer_class: type[DataSeriesSet]  # Type annotation for transformer class

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
    
    def _get_page_size(self) -> int:
        """Get the configured page size for paginated queries.
        
        Returns:
            int: Page size for pagination (default: 365)
        """
        return int(current_app.config.get("STATS_DATA_SERIES_PAGE_SIZE", 365))
    
    def _calculate_series_count(self, series_set: DataSeriesSet) -> int:
        """Calculate the number of series arrays based on transformer structure.
        
        Args:
            series_set: The DataSeriesSet instance that will be used.
            
        Returns:
            int: Total number of series arrays that will be created.
        """
        # Use the already-created transformer instance
        series_keys = series_set.series_keys
        discovered_metrics = series_set._get_default_metrics()
        special_subcounts = series_set.special_subcounts
        
        total_count = 0
        for subcount in series_keys:
            if subcount in special_subcounts:
                special_metrics = series_set._get_special_subcount_metrics(subcount)
                if special_metrics:
                    total_count += len(special_metrics)
                else:
                    total_count += len(discovered_metrics["subcount"])
            else:
                if subcount == "global":
                    total_count += len(discovered_metrics["global"])
                else:
                    total_count += len(discovered_metrics["subcount"])
        
        return total_count

    def _measure_sample_document_bytes(
        self,
        search_index: str,
        must_clauses: list[dict],
    ) -> int | None:
        """Fetch a single sample document and measure its serialized size.
        
        This provides a more accurate initial estimate for bytes_per_doc
        than using a config default.
        
        Args:
            search_index: The index to search
            must_clauses: Query clauses for the search
            
        Returns:
            Size in bytes of a sample document, or None if unable to fetch.
        """
        try:
            sample_search = (
                Search(using=self.client, index=search_index)
                .query(Q("bool", must=must_clauses))
                .extra(size=1)
            )
            response = sample_search.execute()
            hits = response.hits.hits
            
            if not hits:
                return None
            
            # Get the _source document (AttrDict)
            sample_doc = hits[0]["_source"]
            
            # Serialize to measure actual byte size (as orjson would)
            # Convert AttrDict to dict for serialization
            doc_dict = dict(sample_doc) if hasattr(sample_doc, "keys") else sample_doc
            serialized_bytes = orjson.dumps(
                doc_dict, option=orjson.OPT_NAIVE_UTC
            )
            
            return len(serialized_bytes)
        except Exception as e:
            current_app.logger.debug(
                f"Failed to fetch sample document for size estimation: {e}"
            )
            return None

    def _fetch_documents_paginated_and_add(
        self,
        search_index: str,
        must_clauses: list[dict],
        date_field: str,
        series_set: DataSeriesSet,
        total_count: int | None = None,
    ) -> None:
        """Fetch documents using pagination and add them incrementally.
        
        This method processes documents page by page, adding each page to the
        series set and then releasing the page from memory before fetching the next.
        Includes memory health checks to adaptively adjust page size.
        
        Args:
            search_index: The index to search
            must_clauses: Query clauses for the search
            date_field: Field to sort by (also used for search_after)
            series_set: DataSeriesSet instance to add documents to
            total_count: Total number of documents in the query (for memory estimation)
        """
        initial_page_size = self._get_page_size()
        series_count = self._calculate_series_count(series_set)
        
        # Fetch a sample document to get accurate initial size estimate
        sample_doc_bytes = self._measure_sample_document_bytes(
            search_index, must_clauses
        )
        
        estimator = DataSeriesMemoryEstimator(
            series_count=series_count,
            initial_page_size=initial_page_size,
            total_count=total_count,
            sample_doc_bytes=sample_doc_bytes,
        )
        current_page_size = estimator.get_current_page_size()
        
        days_processed = 0
        search_after = None
        iteration_count = 0
        max_iterations = 10000  # Safety limit: should never be reached
        
        while iteration_count < max_iterations:
            iteration_count += 1
            
            agg_search = (
                Search(using=self.client, index=search_index)
                .query(Q("bool", must=must_clauses))
                .extra(size=current_page_size)
            )
            agg_search.sort(date_field, "_id")
            
            if search_after:
                agg_search = agg_search.extra(search_after=search_after)
            
            try:
                response = agg_search.execute()
                hits = response.hits.hits
                
                if not hits:
                    break
                
                # Extract sort value from last hit before processing documents
                last_hit = hits[-1] if hits else None
                next_search_after = None
                if last_hit:
                    # Extract sort values from the last hit's metadata
                    if hasattr(last_hit.meta, "sort") and last_hit.meta.sort:
                        sort_values = last_hit.meta.sort
                        if len(sort_values) >= 2:
                            next_search_after = [sort_values[0], sort_values[1]]
                
                # Extract documents for this page
                # Note: h["_source"] is an AttrDict, which supports dict-like
                # operations. We use it directly to avoid the memory overhead
                # of .to_dict() conversion. Transformers use .get() which works
                # fine with AttrDict.
                page_documents = [h["_source"] for h in hits]
                
                # Process this page
                series_set.add(page_documents)
                page_count = len(page_documents)
                days_processed += page_count
                
                # Capture RSS with page in memory (before cleanup) on first iteration
                if iteration_count == 1:
                    estimator.capture_page_rss()
                
                # Clear the page from memory immediately
                del hits
                del page_documents
                del response
                gc.collect()
                
                # Update page size (re-estimates if first page, then adjusts)
                current_page_size = estimator.update_page_size(days_processed)
                
                # Break if we got fewer results than page size (end of results)
                if page_count < current_page_size:
                    break
                
                # Update search_after for next iteration
                search_after = next_search_after
                
                # If we couldn't get search_after, break (safety check)
                if not search_after:
                    current_app.logger.warning(
                        f"Could not extract search_after from last hit, "
                        f"stopping pagination at iteration {iteration_count}"
                    )
                    break
                
                # Log progress every 100 iterations as a sanity check
                if iteration_count % 100 == 0:
                    current_app.logger.debug(
                        f"Pagination progress: iteration {iteration_count}, "
                        f"page_size: {current_page_size}, "
                        f"search_after: {search_after}, "
                        f"days_processed: {days_processed}"
                    )
                
            except Exception as e:
                current_app.logger.error(
                    f"Error fetching paginated documents at iteration "
                    f"{iteration_count}: {e}"
                )
                break
        
        if iteration_count >= max_iterations:
            current_app.logger.error(
                f"Pagination hit maximum iteration limit ({max_iterations}). "
                f"This should never happen and indicates a bug."
            )

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Base implementation returns the index as-is. Child classes can override
        to append the date_basis suffix.

        Returns:
            str: The index to be used for the date basis query.
        """
        return str(self.index)

    def run(
        self,
        community_id: str = "global",
        start_date: str | None = None,
        end_date: str | None = None,
        category: str = "global",
        metric: str = "views",
        subcount_id: str | None = None,
        date_basis: str = "added",
    ) -> Response | list[DataSeriesDict] | dict | list:
        """Run the query to generate a single data series.

        Args:
            community_id: The community ID (UUID or slug). If "global", the
                query will be run for the entire repository. Default is "global".
            start_date: The start date. Can be a date string parseable by
                arrow.get() or a datetime object.
            end_date: The end date. Can be a date string parseable by
                arrow.get() or a datetime object.
            category: The category of the series ('global', 'access_statuses', etc.)
            metric: The metric type ('views', 'downloads', 'visitors', 'dataVolume')
            subcount_id: Specific subcount item ID (for subcount series)
            date_basis: The date basis for the query ("added", "created",
                "published"). Default is "added".

        Raises:
            ValueError: if the community can't be found.
            AssertionError: if the index doesn't exist.

        Returns:
            DataSeries object or Response with serialized data
        """
        if community_id != "global":
            try:
                community = current_communities.service.read(
                    system_identity, community_id
                )
                community_id = community.id
            except Exception as e:
                raise ValueError(f"Community {community_id} not found: {str(e)}") from e

        search_index = self._get_index_for_date_basis(date_basis)

        must_clauses: list[dict] = [
            {"term": {"community_id": community_id}},
        ]
        range_clauses: dict[str, dict[str, str]] = {self.date_field: {}}
        if start_date:
            range_clauses[self.date_field]["gte"] = (
                arrow.get(start_date).floor("day").format("YYYY-MM-DDTHH:mm:ss")
            )
        if end_date:
            range_clauses[self.date_field]["lte"] = (
                arrow.get(end_date).ceil("day").format("YYYY-MM-DDTHH:mm:ss")
            )
        if range_clauses:
            must_clauses.append({"range": range_clauses})

        index_pattern = f"{search_index}-*"

        try:
            if self.client.indices.exists_alias(name=search_index):
                final_search_index = search_index
            else:
                indices = self.client.indices.get(index_pattern)
                if not indices:
                    raise AssertionError(
                        f"No indices found for alias '{search_index}' or pattern "
                        f"{index_pattern}'"
                    )
                final_search_index = index_pattern

            # Get total count for memory estimation
            count_search = (
                Search(using=self.client, index=final_search_index)
                .query(Q("bool", must=must_clauses))
            )
            total_count = count_search.count()
            
            if total_count == 0:
                # Return empty data series instead of raising an exception
                # This allows the UI to display zero-filled charts for empty years
                current_app.logger.info(
                    f"No results found for community {community_id}"
                    f" for the period {start_date} to {end_date} - "
                    f"returning empty data series"
                )
                # Create empty data series set
                if category == "global":
                    series_keys = ["global"]
                else:
                    series_keys = [category]
                series_set = self.transformer_class(
                    documents=[], series_keys=series_keys
                )
            else:
                # Create data series set with empty initial list
                # For single series queries, we need to include the specific category
                if category == "global":
                    series_keys = ["global"]
                else:
                    series_keys = [category]
                series_set = self.transformer_class(
                    documents=[], series_keys=series_keys
                )
                
                # Fetch and add documents incrementally using pagination
                self._fetch_documents_paginated_and_add(
                    final_search_index,
                    must_clauses,
                    self.date_field,
                    series_set,
                    total_count,
                )
                
        except AssertionError as e:
            current_app.logger.error(f"Index does not exist: {self.index} {e}")
            # Create empty data series set
            if category == "global":
                series_keys = ["global"]
            else:
                series_keys = [category]
            series_set = self.transformer_class(
                documents=[], series_keys=series_keys
            )

        # Get the complete data series set with camelCase conversion
        json_result = series_set.for_json()

        # Extract the requested data series
        if category == "global":
            # For global, get the specific metric from the global section
            if "global" in json_result and metric in json_result["global"]:
                series_data = json_result["global"][metric]
            else:
                series_data = []
        else:
            # For subcount, get the specific category and metric
            if category in json_result and metric in json_result[category]:
                series_data = json_result[category][metric]
            else:
                series_data = []

        # Return raw data only - content negotiation handled by view
        return series_data


class UsageSnapshotDataSeriesQuery(DataSeriesQueryBase):
    """Query for usage snapshot data series."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"
        self.transformer_class = UsageSnapshotDataSeriesSet


class UsageDeltaDataSeriesQuery(DataSeriesQueryBase):
    """Query for usage delta data series."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"
        self.transformer_class = UsageDeltaDataSeriesSet


class RecordSnapshotDataSeriesQuery(DataSeriesQueryBase):
    """Query for record snapshot data series."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"
        self.transformer_class = RecordSnapshotDataSeriesSet

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Returns:
            str: The full index with date basis appended.
        """
        return f"{self.index}-{date_basis}"


class RecordDeltaDataSeriesQuery(DataSeriesQueryBase):
    """Query for record delta data series."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"
        self.transformer_class = RecordDeltaDataSeriesSet

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Returns:
            str: The full index with date basis appended.
        """
        return f"{self.index}-{date_basis}"


class CategoryDataSeriesQueryBase(DataSeriesQueryBase):
    """Base class for category-wide data series queries."""
    
    # Inherits all methods from DataSeriesQueryBase:
    # - _get_page_size()
    # - _calculate_series_count()
    # - _measure_sample_document_bytes()
    # - _fetch_documents_paginated_and_add()

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Base implementation returns the index as-is. Child classes can override
        to append the date_basis suffix.

        Returns:
            str: Index name.
        """
        return str(self.index)

    def run(  # type: ignore[override]
        self,
        community_id: str = "global",
        start_date: str | None = None,
        end_date: str | None = None,
        date_basis: str = "added",
    ) -> Response | dict[str, dict[str, list[DataSeriesDict]]] | dict | list:
        """Run the query to generate all data series for a category.

        Args:
            community_id: The community ID (UUID or slug). If "global", the
                query will be run for the entire repository. Default is "global".
            start_date: The start date. Can be a date string parseable by
                arrow.get() or a datetime object.
            end_date: The end date. Can be a date string parseable by
                arrow.get() or a datetime object.
            date_basis: The date basis for the query ("added", "created",
                "published"). Default is "added".

        Raises:
            ValueError: if the community can't be found.
            AssertionError: if the index doesn't exist.

        Returns:
            Dictionary of DataSeries objects or Response with serialized data
        """
        if community_id != "global":
            try:
                community = current_communities.service.read(
                    system_identity, community_id
                )
                community_id = community.id
            except Exception as e:
                raise ValueError(f"Community {community_id} not found: {str(e)}") from e

        search_index = self._get_index_for_date_basis(date_basis)

        # Build search query
        must_clauses: list[dict] = [
            {"term": {"community_id": community_id}},
        ]
        range_clauses: dict[str, dict[str, str]] = {self.date_field: {}}
        if start_date:
            range_clauses[self.date_field]["gte"] = (
                arrow.get(start_date).floor("day").format("YYYY-MM-DDTHH:mm:ss")
            )
        if end_date:
            range_clauses[self.date_field]["lte"] = (
                arrow.get(end_date).ceil("day").format("YYYY-MM-DDTHH:mm:ss")
            )
        if range_clauses:
            must_clauses.append({"range": range_clauses})

        # Execute search
        index_pattern = f"{search_index}-*"

        try:
            if self.client.indices.exists_alias(name=search_index):
                final_search_index = search_index
            else:
                indices = self.client.indices.get(index_pattern)
                if not indices:
                    raise AssertionError(
                        f"No indices found for alias '{search_index}' or pattern "
                        f"{index_pattern}'"
                    )
                final_search_index = index_pattern

            # Get total count for memory estimation
            count_search = (
                Search(using=self.client, index=final_search_index)
                .query(Q("bool", must=must_clauses))
            )
            total_count = count_search.count()
            
            if total_count == 0:
                # Return empty data series instead of raising an exception
                # This allows the UI to display zero-filled charts for empty years
                current_app.logger.info(
                    f"No results found for community {community_id}"
                    f" for the period {start_date} to {end_date} - "
                    f"returning empty data series"
                )
                # Create empty data series set
                series_set = self.transformer_class(
                    documents=[],
                    series_keys=None,  # None means use all available
                )
            else:
                # Create data series set with empty initial list
                series_set = self.transformer_class(
                    documents=[],
                    series_keys=None,  # None means use all available
                )
                
                # Fetch and add documents incrementally using pagination
                self._fetch_documents_paginated_and_add(
                    final_search_index,
                    must_clauses,
                    self.date_field,
                    series_set,
                    total_count,
                )
                
        except AssertionError as e:
            current_app.logger.error(f"Index does not exist: {self.index} {e}")
            # Create empty data series set
            series_set = self.transformer_class(
                documents=[],
                series_keys=None,  # None means use all available
            )

        # Get the complete data series set with camelCase conversion
        json_result = series_set.for_json()

        # Return raw data only - content negotiation handled by view
        return json_result


class UsageSnapshotCategoryQuery(CategoryDataSeriesQueryBase):
    """Query for all usage snapshot data series in a category."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"
        self.transformer_class = UsageSnapshotDataSeriesSet


class UsageDeltaCategoryQuery(CategoryDataSeriesQueryBase):
    """Query for all usage delta data series in a category."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"
        self.transformer_class = UsageDeltaDataSeriesSet


class RecordSnapshotCategoryQuery(CategoryDataSeriesQueryBase):
    """Query for all record snapshot data series in a category."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "snapshot_date"
        self.transformer_class = RecordSnapshotDataSeriesSet

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Returns:
            str: The full index name with date basis appended.
        """
        return f"{self.index}-{date_basis}"


class RecordDeltaCategoryQuery(CategoryDataSeriesQueryBase):
    """Query for all record delta data series in a category."""

    def __init__(
        self, name: str, index: str, client: OpenSearch | None = None, *args, **kwargs
    ):
        """Initialize the query."""
        super().__init__(name, index, client, *args, **kwargs)
        self.date_field = "period_start"
        self.transformer_class = RecordDeltaDataSeriesSet

    def _get_index_for_date_basis(self, date_basis: str) -> str:
        """Get the appropriate index based on date_basis.

        Returns:
            str: The full index name with date basis appended.
        """
        return f"{self.index}-{date_basis}"
