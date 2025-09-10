// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { readableGranularDate, formatDate, formatDateRange } from "./dates";

// Mock i18next
jest.mock("@translations/invenio_stats_dashboard/i18next", () => ({
  i18next: {
    language: "en",
    t: (key) => key === "Q" ? "Q" : key,
  },
}));

describe("readableGranularDate", () => {
  it("formats day granularity correctly", () => {
    const result = readableGranularDate("2024-01-15", "day");
    expect(result).toBe("Jan 15, 2024");
  });

  it("formats week granularity correctly", () => {
    const result = readableGranularDate("2024-01-15", "week");
    expect(result).toBe("Jan 15 – 21, 2024");
  });

  it("formats week granularity correctly for end of month", () => {
    const result = readableGranularDate("2024-01-29", "week");
    expect(result).toBe("Jan 29 – Feb 4, 2024");
  });

  it("formats month granularity correctly", () => {
    const result = readableGranularDate("2024-01-15", "month");
    expect(result).toBe("January 2024");
  });

  it("formats quarter granularity correctly", () => {
    const result = readableGranularDate("2024-01-15", "quarter");
    expect(result).toBe("Q1 2024");
  });

  it("formats year granularity correctly", () => {
    const result = readableGranularDate("2024-01-15", "year");
    expect(result).toBe("2024");
  });

  it("formats different quarters correctly", () => {
    expect(readableGranularDate("2024-04-15", "quarter")).toBe("Q2 2024");
    expect(readableGranularDate("2024-07-15", "quarter")).toBe("Q3 2024");
    expect(readableGranularDate("2024-10-15", "quarter")).toBe("Q4 2024");
  });

  it("handles Date object inputs", () => {
    const date = new Date("2024-01-15T10:30:00Z");
    expect(readableGranularDate(date, "day")).toBe("Jan 15, 2024");
    expect(readableGranularDate(date, "month")).toBe("January 2024");
    expect(readableGranularDate(date, "year")).toBe("2024");
    expect(readableGranularDate(date, "quarter")).toBe("Q1 2024");
  });

  it("handles year string inputs", () => {
    expect(readableGranularDate("2024", "year")).toBe("2024");
    expect(readableGranularDate("2024", "month")).toBe("January 2024");
    expect(readableGranularDate("2024", "day")).toBe("Jan 1, 2024");
    expect(readableGranularDate("2024", "quarter")).toBe("Q1 2024");
  });
});

describe("dates", () => {
  describe("formatDate", () => {
    it("formats dates with useShortMonth", () => {
      const date = new Date("2024-01-15T10:30:00Z");
      const result = formatDate(date, 'day', true);
      expect(result).toBe("Jan 15, 2024");
    });

    it("handles null input", () => {
      const result = formatDate(null);
      expect(result).toBe("");
    });

    it("handles undefined input", () => {
      const result = formatDate(undefined);
      expect(result).toBe("");
    });

    describe("with string inputs", () => {
      it("handles quarter strings", () => {
        const result = formatDate("2024-Q1");
        expect(result).toBe("Q1 2024");
      });

      it("handles month strings", () => {
        const result = formatDate("2024-01", 'month');
        expect(result).toBe("January 2024");
      });

      it("handles month strings with short month", () => {
        const result = formatDate("2024-01", 'month', true);
        expect(result).toBe("Jan 2024");
      });

      it("handles year strings", () => {
        const result = formatDate("2024", 'year');
        expect(result).toBe("2024");
      });

      it("handles year strings with different granularities", () => {
        expect(formatDate("2024", 'year')).toBe("2024");
        expect(formatDate("2024", 'month')).toBe("January 2024");
        expect(formatDate("2024", 'day')).toBe("January 1, 2024");
        expect(formatDate("2024", 'quarter')).toBe("Q1 2024");
      });

      it("handles full date strings", () => {
        const result = formatDate("2024-01-15");
        expect(result).toBe("January 15, 2024");
      });
    });

    describe("with Date object inputs", () => {
      it("handles Date objects with different granularities", () => {
        const date = new Date("2024-01-15T10:30:00Z");
        expect(formatDate(date, 'day')).toBe("January 15, 2024");
        expect(formatDate(date, 'month')).toBe("January 2024");
        expect(formatDate(date, 'year')).toBe("2024");
        expect(formatDate(date, 'quarter')).toBe("Q1 2024");
      });

      it("handles Date objects with short month format", () => {
        const date = new Date("2024-01-15T10:30:00Z");
        expect(formatDate(date, 'day', true)).toBe("Jan 15, 2024");
        expect(formatDate(date, 'month', true)).toBe("Jan 2024");
      });

      it("handles Date objects with different times", () => {
        const morning = new Date("2024-01-15T08:00:00Z");
        const evening = new Date("2024-01-15T20:00:00Z");
        expect(formatDate(morning, 'day')).toBe("January 15, 2024");
        expect(formatDate(evening, 'day')).toBe("January 15, 2024");
      });
    });

    describe("with date ranges", () => {
      const startDate = new Date("2024-01-01T00:00:00.000Z");
      const endDate = new Date("2024-12-31T00:00:00.000Z");

      it("formats start date in range", () => {
        const result = formatDate(startDate, 'day', false, endDate);
        expect(result).toMatch(/January 1\s+.*\s+December 31, 2024/);
      });

      it("formats start date in range with short month", () => {
        const result = formatDate(startDate, 'day', true, endDate);
        expect(result).toMatch(/Jan 1\s+.*\s+Dec 31, 2024/);
      });

      it("formats end date in range", () => {
        const result = formatDate(endDate, 'day', false);
        expect(result).toBe("December 31, 2024");
      });
    });
  });

  describe("formatDateRange", () => {
    const dateRange = {
      start: new Date("2024-01-01T00:00:00.000Z"),
      end: new Date("2024-01-07T00:00:00.000Z")
    };

    it("formats date range with default options", () => {
      const result = formatDateRange(dateRange);
      expect(result).toMatch(/January 1\s+.*\s+7, 2024/);
    });

    it("formats date range with year granularity", () => {
      const result = formatDateRange(dateRange, 'year', false);
      expect(result).toBe("2024");
    });

    it("formats date range with month granularity", () => {
      const result = formatDateRange(dateRange, 'month', false);
      expect(result).toBe("January 2024");
    });

    it("formats date range with quarter granularity", () => {
      const result = formatDateRange(dateRange, 'quarter', false);
      expect(result).toBe("Q1 2024 – Q1 2024");
    });

    it("handles null input", () => {
      const result = formatDateRange(null);
      expect(result).toBe("");
    });

    it("handles undefined input", () => {
      const result = formatDateRange(undefined);
      expect(result).toBe("");
    });

    it("handles empty dateRange", () => {
      const result = formatDateRange({});
      expect(result).toBe("");
    });

    it("handles missing start", () => {
      const result = formatDateRange({ end: new Date() });
      expect(result).toBe("");
    });

    it("handles missing end", () => {
      const result = formatDateRange({ start: new Date() });
      expect(result).toBe("");
    });
  });

  describe("edge cases", () => {
    it("should handle invalid date strings gracefully", () => {
      expect(() => formatDate("invalid-date")).toThrow();
    });

    it("should handle empty string", () => {
      const result = formatDate("");
      expect(result).toBe("");
    });

    it("should handle different date formats", () => {
      expect(formatDate("2024-01-15T10:30:00Z")).toMatch(/January 15, 2024/);
      expect(formatDate("2024-01-15T10:30:00")).toMatch(/January 15, 2024/);
    });

    it("should handle invalid Date objects gracefully", () => {
      const invalidDate = new Date("invalid");
      expect(() => formatDate(invalidDate)).toThrow();
    });

    it("should handle Date objects with extreme values", () => {
      const farFuture = new Date("2100-12-31T23:59:59Z");
      const farPast = new Date("1900-01-01T00:00:00Z");
      expect(formatDate(farFuture, 'year')).toBe("2100");
      expect(formatDate(farPast, 'year')).toBe("1900");
    });
  });
});