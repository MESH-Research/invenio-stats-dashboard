// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { filterSeriesArrayByDate } from "./filters";

describe("filterSeriesArrayByDate", () => {
  it("should filter series array by date", () => {
    const seriesArray = [
      {
        id: "series-1",
        name: "Series 1",
        data: [
          { value: [new Date(Date.UTC(2024, 0, 1)), 10] },
          { value: [new Date(Date.UTC(2024, 0, 2)), 20] },
          { value: [new Date(Date.UTC(2024, 0, 3)), 30] },
          { value: [new Date(Date.UTC(2024, 0, 4)), 40] },
          { value: [new Date(Date.UTC(2024, 0, 5)), 50] },
        ],
        type: "line",
        valueType: "number",
      },
      {
        id: "series-2",
        name: "Series 2",
        data: [
          { value: [new Date(Date.UTC(2024, 0, 1)), 10] },
          { value: [new Date(Date.UTC(2024, 0, 2)), 20] },
          { value: [new Date(Date.UTC(2024, 0, 3)), 30] },
          { value: [new Date(Date.UTC(2024, 0, 4)), 40] },
          { value: [new Date(Date.UTC(2024, 0, 5)), 50] },
        ],
        type: "line",
        valueType: "number",
      },
    ];
    const dateRange = {
      start: new Date(Date.UTC(2024, 0, 2)),
      end: new Date(Date.UTC(2024, 0, 4))
    };
    const filteredSeriesArray = filterSeriesArrayByDate(seriesArray, dateRange);
    expect(filteredSeriesArray).toEqual([
      {
        id: "series-1",
        name: "Series 1",
        type: "line",
        valueType: "number",
        data: [
          { value: [new Date(Date.UTC(2024, 0, 2)), 20] },
          { value: [new Date(Date.UTC(2024, 0, 3)), 30] },
          { value: [new Date(Date.UTC(2024, 0, 4)), 40] },
        ],
      },
      {
        id: "series-2",
        name: "Series 2",
        type: "line",
        valueType: "number",
        data: [
          { value: [new Date(Date.UTC(2024, 0, 2)), 20] },
          { value: [new Date(Date.UTC(2024, 0, 3)), 30] },
          { value: [new Date(Date.UTC(2024, 0, 4)), 40] },
        ],
      },
    ]);
  });

  it("should filter series array by date with latestOnly", () => {
    const seriesArray = [
      {
        id: "series-1",
        name: "Series 1",
        data: [
          { value: [new Date(Date.UTC(2024, 0, 1)), 10] },
          { value: [new Date(Date.UTC(2024, 0, 2)), 20] },
          { value: [new Date(Date.UTC(2024, 0, 3)), 30] },
          { value: [new Date(Date.UTC(2024, 0, 4)), 40] },
          { value: [new Date(Date.UTC(2024, 0, 5)), 50] },
        ],
        type: "line",
        valueType: "number",
      },
    ];
    const dateRange = { start: new Date(Date.UTC(2024, 0, 2)), end: new Date(Date.UTC(2024, 0, 4)) };
    const filteredSeriesArray = filterSeriesArrayByDate(seriesArray, dateRange, true);
    expect(filteredSeriesArray).toEqual([
      {
        id: "series-1",
        name: "Series 1",
        type: "line",
        valueType: "number",
        data: [{ value: [new Date(Date.UTC(2024, 0, 4)), 40] }],
      },
    ]);
  });

  it("should return empty array if series array is empty", () => {
    const seriesArray = [];
    const dateRange = { start: new Date(Date.UTC(2024, 0, 2)), end: new Date(Date.UTC(2024, 0, 4)) };
    const filteredSeriesArray = filterSeriesArrayByDate(seriesArray, dateRange);
    expect(filteredSeriesArray).toEqual([]);
  });

  it("should return the original array if date range is empty", () => {
    const seriesArray = [
      {
        id: "series-1",
        name: "Series 1",
        data: [{ value: [new Date(Date.UTC(2024, 0, 1)), 10] }],
        type: "line",
        valueType: "number",
      },
    ];
    const dateRange = {};
    const filteredSeriesArray = filterSeriesArrayByDate(seriesArray, dateRange);
    expect(filteredSeriesArray).toEqual([
      {
        id: "series-1",
        name: "Series 1",
        type: "line",
        valueType: "number",
        data: [{ value: [new Date(Date.UTC(2024, 0, 1)), 10] }],
      },
    ]);
  });

  it("should return only the latest data point when date range is empty and latestOnly is true", () => {
    const seriesArray = [
      {
        id: "series-1",
        name: "Series 1",
        data: [
          { value: [new Date(Date.UTC(2024, 0, 1)), 10] },
          { value: [new Date(Date.UTC(2024, 0, 2)), 20] },
          { value: [new Date(Date.UTC(2024, 0, 3)), 30] },
        ],
        type: "line",
        valueType: "number",
      },
    ];
    const dateRange = {};
    const filteredSeriesArray = filterSeriesArrayByDate(seriesArray, dateRange, true);
    expect(filteredSeriesArray).toEqual([
      {
        id: "series-1",
        name: "Series 1",
        type: "line",
        valueType: "number",
        data: [{ value: [new Date(Date.UTC(2024, 0, 3)), 30] }],
      },
    ]);
  });

  it("should return series with empty data if no array items fall within date range", () => {
    const seriesArray = [
      {
        id: "series-1",
        name: "Series 1",
        data: [{ value: [new Date(Date.UTC(2024, 0, 1)), 10] }],
        type: "line",
        valueType: "number",
      },
    ];
    const dateRange = { start: new Date(Date.UTC(2024, 0, 2)), end: new Date(Date.UTC(2024, 0, 4)) };
    const filteredSeriesArray = filterSeriesArrayByDate(seriesArray, dateRange);
    expect(filteredSeriesArray).toEqual([
      {
        id: "series-1",
        name: "Series 1",
        type: "line",
        valueType: "number",
        data: [],
      },
    ]);
  });

  it("should return filtered series array even if data points are out of date order", () => {
    const seriesArray = [
      {
        id: "series-1",
        name: "Series 1",
        data: [
          { value: [new Date(Date.UTC(2024, 0, 3)), 30] },
          { value: [new Date(Date.UTC(2024, 0, 4)), 40] },
          { value: [new Date(Date.UTC(2024, 0, 2)), 20] },
          { value: [new Date(Date.UTC(2024, 0, 1)), 10] },
          { value: [new Date(Date.UTC(2024, 0, 5)), 50] },
        ],
        type: "line",
        valueType: "number",
      },
    ];
    const dateRange = { start: new Date(Date.UTC(2024, 0, 2)), end: new Date(Date.UTC(2024, 0, 4)) };
    const filteredSeriesArray = filterSeriesArrayByDate(seriesArray, dateRange);
    expect(filteredSeriesArray).toEqual([
      {
        id: "series-1",
        name: "Series 1",
        type: "line",
        valueType: "number",
        data: [
          { value: [new Date(Date.UTC(2024, 0, 3)), 30] },
          { value: [new Date(Date.UTC(2024, 0, 4)), 40] },
          { value: [new Date(Date.UTC(2024, 0, 2)), 20] },
        ],
      },
    ]);
  });
});
