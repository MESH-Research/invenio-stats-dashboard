import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import * as echarts from 'echarts';
import ReactECharts from 'echarts-for-react';
import worldJson from './data/world2.json';
import { COUNTRY_NAME_MAP } from './data/country_mappings';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { Header, Segment } from 'semantic-ui-react';
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
  const { stats, dateRange } = useStatsDashboard();

  useEffect(() => {
    // Register the world map
    echarts.registerMap('world', worldJson);
    setIsMapRegistered(true);
  }, []);

  const mapData = extractCountryMapData(stats, metric, dateRange, COUNTRY_NAME_MAP, useSnapshot);

  const maxValue = Math.max(...mapData.map(item => item.value), 1);

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
        {isMapRegistered ? (
          <ReactECharts
            option={option}
            notMerge={true}
            style={{ height: height, minHeight: minHeight }}
            className="stats-map"
          />
        ) : (
          <div>Loading map...</div>
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