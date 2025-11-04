// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { getAvailableBreakdowns } from "./breakdownHelpers";

describe("getAvailableBreakdowns", () => {
  it("returns empty array when data is null or empty", () => {
    expect(getAvailableBreakdowns(null)).toEqual([]);
    expect(getAvailableBreakdowns([])).toEqual([]);
    expect(getAvailableBreakdowns(undefined)).toEqual([]);
  });

  it("returns empty array when no breakdowns have data", () => {
    const seriesWithData = { data: [{ value: [new Date(), 10] }] };
    const data = [
      {
        global: { records: [seriesWithData] },
        resourceTypes: { records: [] }, // Empty
      },
    ];

    expect(getAvailableBreakdowns(data)).toEqual([]);
  });

  it("finds breakdowns with data in first yearly block", () => {
    const series1 = { data: [{ value: [new Date(), 10] }] };
    const series2 = { data: [{ value: [new Date(), 5] }] };
    const series3 = { data: [{ value: [new Date(), 3] }] };
    const data = [
      {
        global: { records: [series1] },
        resourceTypes: {
          records: [series2],
        },
        subjects: {
          records: [series3],
        },
      },
    ];

    const result = getAvailableBreakdowns(data);
    expect(result).toContain("resourceTypes");
    expect(result).toContain("subjects");
    expect(result).not.toContain("global");
  });

  it("finds breakdowns with data in later yearly blocks when first block has zeros", () => {
    const series1 = { data: [{ value: [new Date(), 10] }] };
    const series2 = { data: [{ value: [new Date(), 5] }] };
    const series3 = { data: [{ value: [new Date(), 3] }] };
    const data = [
      {
        year: 2020,
        global: { records: [series1] },
        resourceTypes: { records: [] }, // Empty in first block
        subjects: { records: [] }, // Empty in first block
      },
      {
        year: 2021,
        global: { records: [series1] },
        resourceTypes: {
          records: [series2],
        },
        subjects: {
          records: [series3],
        },
      },
    ];

    const result = getAvailableBreakdowns(data);
    expect(result).toContain("resourceTypes");
    expect(result).toContain("subjects");
  });

  it("filters by date range when provided", () => {
    const series1 = { data: [{ value: [new Date(), 10] }] };
    const series2 = { data: [{ value: [new Date(), 5] }] };
    const series3 = { data: [{ value: [new Date(), 3] }] };
    const series4 = { data: [{ value: [new Date(), 2] }] };
    const data = [
      {
        year: 2020,
        global: { records: [series1] },
        resourceTypes: {
          records: [series2],
        },
      },
      {
        year: 2021,
        global: { records: [series1] },
        subjects: {
          records: [series3],
        },
      },
      {
        year: 2022,
        global: { records: [series1] },
        funders: {
          records: [series4],
        },
      },
    ];

    const dateRange = {
      start: new Date("2021-01-01"),
      end: new Date("2021-12-31"),
    };

    const result = getAvailableBreakdowns(data, dateRange);
    expect(result).toContain("subjects");
    expect(result).not.toContain("resourceTypes"); // 2020, outside range
    expect(result).not.toContain("funders"); // 2022, outside range
  });

  it("includes all blocks when date range spans multiple years", () => {
    const series1 = { data: [{ value: [new Date(), 10] }] };
    const series2 = { data: [{ value: [new Date(), 5] }] };
    const series3 = { data: [{ value: [new Date(), 3] }] };
    const data = [
      {
        year: 2020,
        global: { records: [series1] },
        resourceTypes: {
          records: [series2],
        },
      },
      {
        year: 2021,
        global: { records: [series1] },
        subjects: {
          records: [series3],
        },
      },
    ];

    const dateRange = {
      start: new Date("2020-01-01"),
      end: new Date("2021-12-31"),
    };

    const result = getAvailableBreakdowns(data, dateRange);
    expect(result).toContain("resourceTypes");
    expect(result).toContain("subjects");
  });

  it("handles blocks without year property by including them all", () => {
    const series1 = { data: [{ value: [new Date(), 10] }] };
    const series2 = { data: [{ value: [new Date(), 5] }] };
    const series3 = { data: [{ value: [new Date(), 3] }] };
    const data = [
      {
        // No year property
        global: { records: [series1] },
        resourceTypes: {
          records: [series2],
        },
      },
      {
        // No year property
        global: { records: [series1] },
        subjects: {
          records: [series3],
        },
      },
    ];

    const dateRange = {
      start: new Date("2021-01-01"),
      end: new Date("2021-12-31"),
    };

    // Should include all blocks when no year property exists
    const result = getAvailableBreakdowns(data, dateRange);
    expect(result).toContain("resourceTypes");
    expect(result).toContain("subjects");
  });

  it("only includes breakdowns that have at least one series with data", () => {
    const series1 = { data: [{ value: [new Date(), 10] }] };
    const series2 = { data: [{ value: [new Date(), 5] }] };
    const data = [
      {
        global: { records: [series1] },
        resourceTypes: {
          records: [series2],
          views: [], // Empty array
        },
        subjects: {
          records: [], // Empty
          views: [], // Empty
        },
      },
    ];

    const result = getAvailableBreakdowns(data);
    expect(result).toContain("resourceTypes"); // Has data in records
    expect(result).not.toContain("subjects"); // All arrays empty
  });

  it("skips 'global' key", () => {
    const series1 = { data: [{ value: [new Date(), 10] }] };
    const series2 = { data: [{ value: [new Date(), 5] }] };
    const data = [
      {
        global: { records: [series1] },
        resourceTypes: {
          records: [series2],
        },
      },
    ];

    const result = getAvailableBreakdowns(data);
    expect(result).not.toContain("global");
    expect(result).toContain("resourceTypes");
  });
});

