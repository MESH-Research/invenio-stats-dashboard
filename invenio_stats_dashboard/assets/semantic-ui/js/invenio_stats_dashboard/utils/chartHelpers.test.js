// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { ChartDataProcessor } from "./chartHelpers";

// Mock i18next
jest.mock("@translations/invenio_stats_dashboard/i18next", () => ({
  i18next: {
    t: (key) => key,
    language: "en",
  },
}));

// Mock i18n helper
jest.mock("./i18n", () => ({
  extractLocalizedLabel: (label, language) => label,
}));

// Mock nameTransformHelpers
jest.mock("./nameTransformHelpers", () => ({
  getLicenseLabelForms: (id, name) => ({
    short: name,
    long: name,
    isAbbreviated: false,
  }),
}));

// Mock filters
jest.mock("./filters", () => ({
  filterSeriesArrayByDate: (seriesArray, dateRange, latestOnly) => {
    // Simple mock: return series as-is for testing selectTopSeries behavior
    // The actual filtering logic is tested in filters.test.js
    return seriesArray;
  },
}));

// Mock dates helper
jest.mock("./dates", () => ({
  readableGranularDate: (date, granularity) => {
    return date.toISOString().split("T")[0];
  },
}));

// Import the internal function by accessing it through a test-friendly approach
// Since selectTopSeries is not exported, we'll test it through prepareDataSeries
// which uses it internally

describe("ChartDataProcessor", () => {
  describe("prepareDataSeries with selectTopSeries", () => {
    const createDateRange = (startDate, endDate) => ({
      start: new Date(startDate),
      end: new Date(endDate),
    });

    describe("cumulative data (isCumulative = true)", () => {
      it("should rank series by latest value, not sum, for cumulative data", () => {
        // Create series where summing would give different ranking than latest value
        // Series A: starts high, ends low (sum=150, latest=20)
        // Series B: starts low, ends high (sum=150, latest=100)
        // Series C: medium throughout (sum=150, latest=50)
        // For cumulative data, Series B should rank first (latest=100), then C (50), then A (20)
        const seriesArray = [
          {
            id: "series-a",
            name: "Series A",
            data: [
              { value: [new Date("2024-01-01"), 100] },
              { value: [new Date("2024-01-02"), 30] },
              { value: [new Date("2024-01-03"), 20] },
            ],
          },
          {
            id: "series-b",
            name: "Series B",
            data: [
              { value: [new Date("2024-01-01"), 10] },
              { value: [new Date("2024-01-02"), 40] },
              { value: [new Date("2024-01-03"), 100] },
            ],
          },
          {
            id: "series-c",
            name: "Series C",
            data: [
              { value: [new Date("2024-01-01"), 50] },
              { value: [new Date("2024-01-02"), 50] },
              { value: [new Date("2024-01-03"), 50] },
            ],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-03");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes", // displaySeparately to trigger selectTopSeries
          "records",
          dateRange,
          3, // maxSeries
          true, // isCumulative = true
          [{ year: 2024, global: { records: [] } }], // originalData
        );

        // Should be ranked by latest value: B (100) > C (50) > A (20)
        expect(result).toHaveLength(3);
        expect(result[0].id).toBe("series-b"); // Latest value: 100
        expect(result[1].id).toBe("series-c"); // Latest value: 50
        expect(result[2].id).toBe("series-a"); // Latest value: 20
      });

      it("should handle cumulative data with single data point", () => {
        const seriesArray = [
          {
            id: "series-a",
            name: "Series A",
            data: [{ value: [new Date("2024-01-01"), 100] }],
          },
          {
            id: "series-b",
            name: "Series B",
            data: [{ value: [new Date("2024-01-01"), 50] }],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-01");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes",
          "records",
          dateRange,
          2,
          true, // isCumulative
          [{ year: 2024, global: { records: [] } }],
        );

        expect(result).toHaveLength(2);
        expect(result[0].id).toBe("series-a"); // 100 > 50
        expect(result[1].id).toBe("series-b");
      });

      it("should limit to maxSeries when cumulative data has more series", () => {
        const seriesArray = Array.from({ length: 15 }, (_, i) => ({
          id: `series-${i}`,
          name: `Series ${i}`,
          data: [
            { value: [new Date("2024-01-01"), 100 - i] }, // Decreasing values
            { value: [new Date("2024-01-02"), 100 - i] },
          ],
        }));

        const dateRange = createDateRange("2024-01-01", "2024-01-02");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes",
          "records",
          dateRange,
          5, // maxSeries = 5
          true, // isCumulative
          [{ year: 2024, global: { records: [] } }],
        );

        // Should return top 5 series (highest latest values)
        expect(result).toHaveLength(5);
        expect(result[0].id).toBe("series-0"); // Latest: 100
        expect(result[1].id).toBe("series-1"); // Latest: 99
        expect(result[2].id).toBe("series-2"); // Latest: 98
        expect(result[3].id).toBe("series-3"); // Latest: 97
        expect(result[4].id).toBe("series-4"); // Latest: 96
      });
    });

    describe("delta data (isCumulative = false)", () => {
      it("should rank series by sum of all data points for delta data", () => {
        // Series A: sum=150 (50+50+50)
        // Series B: sum=100 (10+20+70)
        // Series C: sum=200 (100+50+50)
        // For delta data, Series C should rank first (sum=200), then A (150), then B (100)
        const seriesArray = [
          {
            id: "series-a",
            name: "Series A",
            data: [
              { value: [new Date("2024-01-01"), 50] },
              { value: [new Date("2024-01-02"), 50] },
              { value: [new Date("2024-01-03"), 50] },
            ],
          },
          {
            id: "series-b",
            name: "Series B",
            data: [
              { value: [new Date("2024-01-01"), 10] },
              { value: [new Date("2024-01-02"), 20] },
              { value: [new Date("2024-01-03"), 70] },
            ],
          },
          {
            id: "series-c",
            name: "Series C",
            data: [
              { value: [new Date("2024-01-01"), 100] },
              { value: [new Date("2024-01-02"), 50] },
              { value: [new Date("2024-01-03"), 50] },
            ],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-03");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes",
          "records",
          dateRange,
          3,
          false, // isCumulative = false (delta data)
          [{ year: 2024, global: { records: [] } }],
        );

        // Should be ranked by sum: C (200) > A (150) > B (100)
        expect(result).toHaveLength(3);
        expect(result[0].id).toBe("series-c"); // Sum: 200
        expect(result[1].id).toBe("series-a"); // Sum: 150
        expect(result[2].id).toBe("series-b"); // Sum: 100
      });

      it("should handle delta data with single data point", () => {
        const seriesArray = [
          {
            id: "series-a",
            name: "Series A",
            data: [{ value: [new Date("2024-01-01"), 100] }],
          },
          {
            id: "series-b",
            name: "Series B",
            data: [{ value: [new Date("2024-01-01"), 50] }],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-01");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes",
          "records",
          dateRange,
          2,
          false, // isCumulative = false
          [{ year: 2024, global: { records: [] } }],
        );

        expect(result).toHaveLength(2);
        expect(result[0].id).toBe("series-a"); // Sum: 100
        expect(result[1].id).toBe("series-b"); // Sum: 50
      });
    });

    describe("edge cases", () => {
      it("should handle empty series array", () => {
        const dateRange = createDateRange("2024-01-01", "2024-01-03");
        const result = ChartDataProcessor.prepareDataSeries(
          [],
          "resourceTypes",
          "records",
          dateRange,
          5,
          true,
          [{ year: 2024, global: { records: [] } }],
        );

        expect(result).toHaveLength(0);
      });

      it("should handle series with empty data arrays", () => {
        const seriesArray = [
          {
            id: "series-a",
            name: "Series A",
            data: [],
          },
          {
            id: "series-b",
            name: "Series B",
            data: [{ value: [new Date("2024-01-01"), 100] }],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-01");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes",
          "records",
          dateRange,
          2,
          true,
          [{ year: 2024, global: { records: [] } }],
        );

        // Series with empty data should be filtered out by filterNonZeroSeries
        expect(result).toHaveLength(1);
        expect(result[0].id).toBe("series-b");
      });

      it("should handle series with no data property", () => {
        const seriesArray = [
          {
            id: "series-a",
            name: "Series A",
            // No data property
          },
          {
            id: "series-b",
            name: "Series B",
            data: [{ value: [new Date("2024-01-01"), 100] }],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-01");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes",
          "records",
          dateRange,
          2,
          true,
          [{ year: 2024, global: { records: [] } }],
        );

        // Series with no data should be filtered out
        expect(result).toHaveLength(1);
        expect(result[0].id).toBe("series-b");
      });

      it("should not call selectTopSeries when displaySeparately is null", () => {
        const seriesArray = [
          {
            id: "series-a",
            name: "Series A",
            data: [{ value: [new Date("2024-01-01"), 100] }],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-01");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          null, // displaySeparately = null (global view)
          "records",
          dateRange,
          5,
          true,
          [{ year: 2024, global: { records: [] } }],
        );

        // All series should be included (no filtering by selectTopSeries)
        expect(result).toHaveLength(1);
        expect(result[0].id).toBe("series-a");
      });
    });

    describe("comparison between cumulative and delta ranking", () => {
      it("should produce different rankings for cumulative vs delta data", () => {
        // Series A: starts high, ends low (sum=150, latest=20)
        // Series B: starts low, ends high (sum=150, latest=100)
        // For cumulative: B > A (by latest)
        // For delta: A = B (by sum, so order may vary but should be same total)
        const seriesArray = [
          {
            id: "series-a",
            name: "Series A",
            data: [
              { value: [new Date("2024-01-01"), 100] },
              { value: [new Date("2024-01-02"), 30] },
              { value: [new Date("2024-01-03"), 20] },
            ],
          },
          {
            id: "series-b",
            name: "Series B",
            data: [
              { value: [new Date("2024-01-01"), 10] },
              { value: [new Date("2024-01-02"), 40] },
              { value: [new Date("2024-01-03"), 100] },
            ],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-03");
        
        // Cumulative ranking
        const cumulativeResult = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes",
          "records",
          dateRange,
          2,
          true, // isCumulative = true
          [{ year: 2024, global: { records: [] } }],
        );

        // Delta ranking
        const deltaResult = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes",
          "records",
          dateRange,
          2,
          false, // isCumulative = false
          [{ year: 2024, global: { records: [] } }],
        );

        // Cumulative: B (latest=100) should rank first
        expect(cumulativeResult[0].id).toBe("series-b");
        expect(cumulativeResult[1].id).toBe("series-a");

        // Delta: Both have sum=150, but order should be consistent
        // Series A sum: 100+30+20 = 150
        // Series B sum: 10+40+100 = 150
        // They're equal, so order may vary, but both should be included
        expect(deltaResult).toHaveLength(2);
        expect(deltaResult.map(s => s.id)).toContain("series-a");
        expect(deltaResult.map(s => s.id)).toContain("series-b");
      });
    });

    describe("country breakdowns filtering 'imported'", () => {
      it("should filter out 'imported' from countries breakdown", () => {
        const seriesArray = [
          {
            id: "US",
            name: "United States",
            data: [
              { value: [new Date("2024-01-01"), 100] },
              { value: [new Date("2024-01-02"), 150] },
            ],
          },
          {
            id: "CA",
            name: "Canada",
            data: [
              { value: [new Date("2024-01-01"), 50] },
              { value: [new Date("2024-01-02"), 75] },
            ],
          },
          {
            id: "imported",
            name: "Imported",
            data: [
              { value: [new Date("2024-01-01"), 200] },
              { value: [new Date("2024-01-02"), 250] },
            ],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-02");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "countries",
          "views",
          dateRange,
          10,
          false,
          [{ year: 2024, global: { views: [] } }],
        );

        // "imported" should be filtered out, only real countries should appear
        const resultIds = result.map(s => s.id);
        expect(resultIds).not.toContain("imported");
        expect(resultIds).toContain("US");
        expect(resultIds).toContain("CA");
      });

      it("should filter out 'imported' from countriesByView breakdown", () => {
        const seriesArray = [
          {
            id: "US",
            name: "United States",
            data: [{ value: [new Date("2024-01-01"), 100] }],
          },
          {
            id: "imported",
            name: "Imported",
            data: [{ value: [new Date("2024-01-01"), 200] }],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-01");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "countriesByView",
          "views",
          dateRange,
          10,
          false,
          [{ year: 2024, global: { views: [] } }],
        );

        expect(result.map(s => s.id)).not.toContain("imported");
        expect(result.map(s => s.id)).toContain("US");
      });

      it("should filter out 'imported' from countriesByDownload breakdown", () => {
        const seriesArray = [
          {
            id: "GB",
            name: "United Kingdom",
            data: [{ value: [new Date("2024-01-01"), 50] }],
          },
          {
            id: "imported",
            name: "Imported",
            data: [{ value: [new Date("2024-01-01"), 150] }],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-01");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "countriesByDownload",
          "downloads",
          dateRange,
          10,
          false,
          [{ year: 2024, global: { downloads: [] } }],
        );

        expect(result.map(s => s.id)).not.toContain("imported");
        expect(result.map(s => s.id)).toContain("GB");
      });

      it("should not filter out 'imported' from non-country breakdowns", () => {
        const seriesArray = [
          {
            id: "type-a",
            name: "Type A",
            data: [{ value: [new Date("2024-01-01"), 100] }],
          },
          {
            id: "imported",
            name: "Imported",
            data: [{ value: [new Date("2024-01-01"), 200] }],
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-01");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "resourceTypes", // Not a country breakdown
          "records",
          dateRange,
          10,
          false,
          [{ year: 2024, global: { records: [] } }],
        );

        // For non-country breakdowns, "imported" should be included
        expect(result.map(s => s.id)).toContain("imported");
        expect(result.map(s => s.id)).toContain("type-a");
      });

      it("should discard 'imported' and not include it in 'other' category for countries", () => {
        const seriesArray = [
          {
            id: "US",
            name: "United States",
            data: [
              { value: [new Date("2024-01-01"), 100], readableDate: "2024-01-01", valueType: "number" },
              { value: [new Date("2024-01-02"), 150], readableDate: "2024-01-02", valueType: "number" },
            ],
          },
          {
            id: "CA",
            name: "Canada",
            data: [
              { value: [new Date("2024-01-01"), 50], readableDate: "2024-01-01", valueType: "number" },
              { value: [new Date("2024-01-02"), 75], readableDate: "2024-01-02", valueType: "number" },
            ],
          },
          {
            id: "imported",
            name: "Imported",
            data: [
              { value: [new Date("2024-01-01"), 200], readableDate: "2024-01-01", valueType: "number" },
              { value: [new Date("2024-01-02"), 250], readableDate: "2024-01-02", valueType: "number" },
            ],
          },
        ];

        // Create mock originalData with global series that includes imported
        const originalData = [
          {
            year: 2024,
            global: {
              views: [
                {
                  id: "global",
                  name: "Global",
                  data: [
                    { value: [new Date("2024-01-01"), 350], readableDate: "2024-01-01", valueType: "number" }, // US (100) + CA (50) + imported (200)
                    { value: [new Date("2024-01-02"), 475], readableDate: "2024-01-02", valueType: "number" }, // US (150) + CA (75) + imported (250)
                  ],
                },
              ],
            },
            countries: {
              views: seriesArray,
            },
          },
        ];

        const dateRange = createDateRange("2024-01-01", "2024-01-02");
        const result = ChartDataProcessor.prepareDataSeries(
          seriesArray,
          "countries",
          "views",
          dateRange,
          1, // Only show top 1 (US), so CA should be in "other", imported should be discarded
          false,
          originalData,
        );

        // Should have US (top 1) and "other" (which includes CA, but NOT imported)
        const resultIds = result.map(s => s.id);
        expect(resultIds).not.toContain("imported"); // Should not appear as separate series
        expect(resultIds).toContain("US");
        
        // Find the "other" series
        const otherSeries = result.find(s => s.id === "other");
        expect(otherSeries).toBeDefined();
        // The "other" series should include CA values, but NOT imported
        // Adjusted global = Global - Imported = (350-200, 475-250) = (150, 225)
        // Visible (US) = (100, 150)
        // Other = Adjusted Global - Visible = (150-100, 225-150) = (50, 75) = CA values
        expect(otherSeries.data[0].value[1]).toBe(50); // 150 - 100 (CA value)
        expect(otherSeries.data[1].value[1]).toBe(75); // 225 - 150 (CA value)
      });
    });
  });
});

