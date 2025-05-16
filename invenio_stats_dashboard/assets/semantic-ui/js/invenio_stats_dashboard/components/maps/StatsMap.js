import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { useStatsDashboard } from '../../context/StatsDashboardContext';

const StatsMap = ({ title, height, minHeight }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  const { dateRange } = useStatsDashboard();

  // Dummy data for demonstration
  const dummyData = [
    { name: 'United States', value: 1000 },
    { name: 'United Kingdom', value: 800 },
    { name: 'Germany', value: 600 },
    { name: 'France', value: 500 },
    { name: 'Japan', value: 400 },
    { name: 'Canada', value: 300 },
    { name: 'Australia', value: 250 },
    { name: 'Brazil', value: 200 },
    { name: 'India', value: 150 },
    { name: 'China', value: 100 },
  ];

  useEffect(() => {
    if (chartRef.current) {
      chartInstance.current = echarts.init(chartRef.current);

      const option = {
        title: {
          text: title,
          left: 'center'
        },
        tooltip: {
          trigger: 'item',
          formatter: '{b}: {c} visits'
        },
        visualMap: {
          min: 0,
          max: 1000,
          text: ['High', 'Low'],
          realtime: false,
          calculable: true,
          inRange: {
            color: ['#e0f3f8', '#2c7fb8']
          }
        },
        series: [{
          name: 'Site Visits',
          type: 'map',
          map: 'world',
          roam: true,
          emphasis: {
            label: {
              show: true
            }
          },
          data: dummyData
        }]
      };

      chartInstance.current.setOption(option);
    }

    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
      }
    };
  }, [title, dateRange]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      if (chartInstance.current) {
        chartInstance.current.resize();
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div
      ref={chartRef}
      style={{
        width: '100%',
        height: height || '500px',
        minHeight: minHeight || '400px'
      }}
    />
  );
};

export { StatsMap };