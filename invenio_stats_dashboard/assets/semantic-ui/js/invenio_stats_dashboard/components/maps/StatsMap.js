import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import * as echarts from 'echarts';
import ReactECharts from 'echarts-for-react';
import worldJson from './data/world2.json';
import { COUNTRY_NAME_MAP } from './data/country_mappings';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Header, Segment, Loader, Message } from 'semantic-ui-react';
import { extractCountryMapData } from '../../utils/mapHelpers';

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
  const { stats, dateRange, isLoading } = useStatsDashboard();

  useEffect(() => {
    // Register the world map
    echarts.registerMap('world', worldJson);
    setIsMapRegistered(true);
  }, []);

  const mapData = extractCountryMapData(stats || {}, metric, dateRange, COUNTRY_NAME_MAP, useSnapshot);

  // Debug logging for extracted map data
  console.log('StatsMap - extracted mapData:', mapData);
  console.log('StatsMap - mapData length:', mapData.length);
  console.log('StatsMap - stats structure:', {
    hasUsageSnapshotData: !!stats?.usageSnapshotData,
    hasTopCountriesByView: !!stats.usageSnapshotData?.topCountriesByView,
    hasTopCountriesByDownload: !!stats.usageSnapshotData?.topCountriesByDownload,
    hasByCountries: !!stats.usageSnapshotData?.byCountries,
    topCountriesByViewViews: stats.usageSnapshotData?.topCountriesByView?.views?.length || 0,
    topCountriesByDownloadDownloads: stats.usageSnapshotData?.topCountriesByDownload?.downloads?.length || 0,
    byCountriesViews: stats.usageSnapshotData?.byCountries?.views?.length || 0
  });

  // Use the extracted map data directly
  const finalMapData = mapData;

  const maxValue = Math.max(...mapData.map(item => item.value), 1);

  // Check if there's any data to display
  const hasData = !isLoading && mapData.length > 0 && mapData.some(item => item.value > 0);

  // Debug logging for max value
  console.log('StatsMap - maxValue:', maxValue);

  const option = {
    aria: {
      enabled: true
    },
    tooltip: {
      trigger: 'item',
      fontSize: 14,
      formatter: (params) => {
        if (!params.value || isNaN(params.value)) {
          return `${params.name}: 0`;
        }
        return `${params.data.originalName}: ${params.data.value}`;
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
      <Header as="h3" attached="top">{title}</Header>
      <Segment fluid attached="bottom" className="stats-map pb-0 pt-0 pr-0 pl-0">
      {isLoading ? (
          <div className="stats-map-loading-container" style={{ height: height, minHeight: minHeight }}>
            <Loader active size="large">
              {i18next.t("Loading map data...")}
            </Loader>
          </div>
        ) : !hasData ? (
          <div className="stats-map-no-data-container" style={{ height: height, minHeight: minHeight }}>
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
          <div className="stats-map-loading-container" style={{ height: height, minHeight: minHeight }}>
            <Loader active size="large">
              {i18next.t("Loading map...")}
            </Loader>
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