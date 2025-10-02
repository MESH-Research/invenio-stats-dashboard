// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React, { useEffect, useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import * as echarts from 'echarts';
import ReactECharts from 'echarts-for-react';
import countriesGeoJson from './data/countries.json';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Header, Segment, Loader, Message } from 'semantic-ui-react';
import { extractCountryMapData } from '../../utils/mapHelpers';
import { formatDate } from '../../utils';

const StatsMap = ({
  title,
  height = 500,
  minHeight = 400,
  zoom = 1.2,
  center = [0, -20],
  metric = 'views',
  useSnapshot = true
}) => {
  const [isMapRegistered, setIsMapRegistered] = useState(false);
  const [dateRangeSubtitle, setDateRangeSubtitle] = useState(null);
  const { stats, dateRange, isLoading } = useStatsDashboard();

  useEffect(() => {
    echarts.registerMap('world', countriesGeoJson);
    setIsMapRegistered(true);
  }, []);

  useEffect(() => {
    if (dateRange) {
      const subtitle = useSnapshot
        ? i18next.t("Cumulative totals as of") + " " + formatDate(dateRange.end, 'day', true)
        : i18next.t("from") + " " + formatDate(dateRange.start, 'day', true, dateRange.end) + " " + i18next.t("to") + " " + formatDate(dateRange.end, 'day', true);
      setDateRangeSubtitle(subtitle);
    }
  }, [dateRange, useSnapshot]);

  const mapData = useMemo(() => {
    return extractCountryMapData(stats || [], metric, dateRange, useSnapshot);
  }, [stats, metric, dateRange, useSnapshot]);

  const maxValue = useMemo(() => {
    return Math.max(...mapData.map(item => item.value), 1);
  }, [mapData]);

  const hasData = useMemo(() => {
    return !isLoading && mapData.length > 0 && mapData.some(item => item.value > 0);
  }, [isLoading, mapData]);

  const option = {
    aria: {
      enabled: true
    },
    tooltip: {
      trigger: 'item',
      fontSize: 14,
      formatter: (params) => {
        if (!params.value || isNaN(params.value)) {
          return `${params.data?.readableName || params.name}: 0`;
        }
        return `${params.data?.readableName || params.data?.originalName || params.name}: ${params.data.value}`;
      }
    },
    visualMap: {
      type: 'continuous',
      min: 0,
      max: maxValue,
      left: '5%',
      bottom: '5%',
      text: ['High', 'Low'],
      calculable: true,
      inRange: {
        color: ['#b3cde3', '#023858']
      },
      textStyle: {
        color: '#333'
      }
    },
    series: [
      {
        name: metric === 'views' ? 'Visits' : metric === 'downloads' ? 'Downloads' : metric === 'visitors' ? 'Visitors' : 'Data Volume',
        type: 'map',
        map: 'world',
        roam: true,
        zoom: zoom,
        center: center,
        data: mapData,
        emphasis: {
          label: {
            show: false
          },
          itemStyle: {
            areaColor: '#e67e22'
          }
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 1
        },
        label: {
          show: false
        },
        silent: false,
        select: {
          itemStyle: {
            areaColor: '#e67e22'
          }
        },
        defaultValue: '#b3cde3'
      }
    ]
  };

  return (
    <>
      <Header as="h3" attached="top">
        {title}
        {dateRangeSubtitle && (
          <Header.Subheader className="stats-map-date-range-subtitle">
            {dateRangeSubtitle}
          </Header.Subheader>
        )}
      </Header>
      <Segment fluid attached="bottom" className="stats-map pb-0 pt-0 pr-0 pl-0" style={{ height: height, minHeight: minHeight }}>
      {isLoading ? (
          <div className="stats-map-loading-container">
            <Loader active size="large" />
          </div>
        ) : !hasData ? (
          <div className="stats-map-no-data-container">
            <Message info>
              <Message.Header>{i18next.t("No Data Available")}</Message.Header>
              <p>{i18next.t("No geographic data is available for the selected time period.")}</p>
            </Message>
          </div>
        ) : isMapRegistered ? (
          <ReactECharts
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
  metric: PropTypes.oneOf(['views', 'downloads', 'visitors', 'dataVolume']),
  useSnapshot: PropTypes.bool,
};

export { StatsMap };