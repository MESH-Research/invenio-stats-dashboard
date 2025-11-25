// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useEffect, useState, useMemo } from "react";
import PropTypes from "prop-types";
import * as echarts from "echarts";
import ReactECharts from "echarts-for-react";
import countriesGeoJson from "./data/countries.json";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Header, Segment, Loader, Message } from "semantic-ui-react";
import { extractCountryMapData, calculateMinZoom } from "../../utils/mapHelpers";
import { formatDate, lightenAndDesaturate } from "../../utils";
import { CHART_COLORS } from "../../constants";

const StatsMap = ({
  title,
  height = 500,
  minHeight = 400,
  zoom = 1.2,
  center = [0, -20],
  metric = "views",
  useSnapshot = true,
  uniformColorMode = false,
}) => {
  const [isMapRegistered, setIsMapRegistered] = useState(false);
  const [dateRangeSubtitle, setDateRangeSubtitle] = useState(null);
  const [minZoom, setMinZoom] = useState(Math.max(1, zoom));
  const { stats, dateRange, isLoading } = useStatsDashboard();
  const chartRef = React.useRef(null);
  const containerRef = React.useRef(null);

  useEffect(() => {
    // Only register the map if it hasn't been registered yet
    // Check if map is already registered to prevent duplicate registrations
    const mapInfo = echarts.getMap("world");
    if (!mapInfo) {
      echarts.registerMap("world", countriesGeoJson);
    }
    setIsMapRegistered(true);

    // Cleanup: dispose chart instance on unmount
    return () => {
      if (chartRef.current) {
        const chartInstance = chartRef.current.getEchartsInstance();
        if (chartInstance && !chartInstance.isDisposed()) {
          chartInstance.dispose();
        }
      }
    };
  }, []);

  useEffect(() => {
    if (dateRange) {
      const subtitle = useSnapshot
        ? i18next.t("Cumulative totals as of") +
          " " +
          formatDate(dateRange.end, "day", true)
        : i18next.t("from") +
          " " +
          formatDate(dateRange.start, "day", true, dateRange.end) +
          " " +
          i18next.t("to") +
          " " +
          formatDate(dateRange.end, "day", true);
      setDateRangeSubtitle(subtitle);
    }
  }, [dateRange, useSnapshot]);

  const mapData = useMemo(() => {
    return extractCountryMapData(stats || [], metric, dateRange, useSnapshot);
  }, [stats, metric, dateRange, useSnapshot]);

  const maxValue = useMemo(() => {
    return Math.max(...mapData.map((item) => item.value), 1);
  }, [mapData]);

  const hasData = useMemo(() => {
    return (
      !isLoading && mapData.length > 0 && mapData.some((item) => item.value > 0)
    );
  }, [isLoading, mapData]);

  // Calculate minimum zoom based on actual container dimensions
  // Ensures map fills at least one dimension (width or height)
  useEffect(() => {
    if (!containerRef.current || !isMapRegistered) return;
    
    const container = containerRef.current;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight || height;
    
    const calculatedMinZoom = calculateMinZoom(containerWidth, containerHeight, 2.0, zoom);
    setMinZoom(calculatedMinZoom);
  }, [isMapRegistered, height, zoom]);

  const option = {
    aria: {
      enabled: true,
    },
    tooltip: {
      trigger: "item",
      fontSize: 14,
      formatter: (params) => {
        const countryName = params.data?.readableName || params.data?.originalName || params.name;
        // In uniform color mode, don't show values since there's no scale
        if (uniformColorMode) {
          return countryName;
        }
        if (!params.value || isNaN(params.value)) {
          return `${countryName}: 0`;
        }
        return `${countryName}: ${params.data.value}`;
      },
    },
    visualMap: uniformColorMode
      ? {
          type: "piecewise",
          show: false,
          pieces: [
            { min: 0, max: 0, color: "#b3cde3" },
            { min: 0.0001, max: Infinity, color: lightenAndDesaturate(CHART_COLORS.secondary[1][1], 0.3, 0.05) }, // Light, desaturated orange
          ],
        }
      : {
          type: "continuous",
          min: 0,
          max: maxValue,
          left: "5%",
          bottom: "5%",
          text: ["High", "Low"],
          calculable: true,
          inRange: {
            color: ["#b3cde3", "#023858"],
          },
          textStyle: {
            color: "#333",
          },
        },
    series: [
      {
        name:
          metric === "views"
            ? "Visits"
            : metric === "downloads"
              ? "Downloads"
              : metric === "visitors"
                ? "Visitors"
                : "Data Volume",
        type: "map",
        map: "world",
        roam: true,
        zoom: zoom,
        center: center,
        scaleLimit: {
          min: minZoom,
          max: 10,
        },
        data: mapData,
        emphasis: {
          label: {
            show: false,
          },
          itemStyle: {
            areaColor: "#e67e22",
          },
        },
        itemStyle: {
          borderColor: "#fff",
          borderWidth: 1,
        },
        label: {
          show: false,
        },
        silent: false,
        select: {
          itemStyle: {
            areaColor: "#e67e22",
          },
          label: {
            show: false,
          },
        },
        defaultValue: "#b3cde3",
      },
    ],
  };

  return (
    <>
      <Header as="h3" attached="top" className="rel-mt-1">
        {title}
        {dateRangeSubtitle && (
          <Header.Subheader className="stats-map-date-range-subtitle">
            {dateRangeSubtitle}
          </Header.Subheader>
        )}
      </Header>
      <Segment
        fluid
        attached="bottom"
        className="stats-map pb-0 pt-0 pr-0 pl-0 rel-mb-1"
        style={{ height: height, minHeight: minHeight }}
        ref={containerRef}
      >
        {isLoading ? (
          <div className="stats-map-loading-container">
            <Loader active size="large" />
          </div>
        ) : !hasData ? (
          <div className="stats-map-no-data-container">
            <Message info>
              <Message.Header>{i18next.t("No Data Available")}</Message.Header>
              <p>
                {i18next.t(
                  "No geographic data is available for the selected time period.",
                )}
              </p>
            </Message>
          </div>
        ) : isMapRegistered ? (
          <ReactECharts
            ref={chartRef}
            option={option}
            notMerge={true}
            style={{ height: height, minHeight: minHeight }}
            className="stats-map"
          />
        ) : (
          <div className="stats-map-loading-container">
            <Loader active size="large" />
          </div>
        )}
      </Segment>
    </>
  );
};

StatsMap.propTypes = {
  title: PropTypes.string,
  height: PropTypes.number,
  minHeight: PropTypes.number,
  zoom: PropTypes.number,
  center: PropTypes.arrayOf(PropTypes.number),
  metric: PropTypes.oneOf(["views", "downloads", "visitors", "dataVolume"]),
  useSnapshot: PropTypes.bool,
  width: PropTypes.number,
  uniformColorMode: PropTypes.bool,
};

export { StatsMap };
