import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from '../shared_components/StatsMultiDisplay';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { formatNumber } from "../../utils/numbers";

// Define colors for different series
const SERIES_COLORS = [
  ['red', '#b54f1e'],  // Dark Red
  ['green', '#6c7839'],  // Dark Green
  ['gold', '#b29017'],  // Dark Yellow
  ['teal', '#276f86'],  // Dark Teal
  ['ivy', '#1c4036'],  // Dark Ivy
  ['verdigris', '#669999'], // Verdigris
  ['purple', '#581c87'],  // Dark Purple
  ['grey', '#666666'],  // Grey for "Other"
];

const MostDownloadedRecordsMultiDisplay = ({
  title = undefined,
  icon = "download",
  pageSize = 10,
  headers = [i18next.t("Record"), i18next.t("Downloads")],
  default_view,
  available_views = ["list", "pie", "bar"],
  ...otherProps
}) => {
  const { stats, isLoading } = useStatsDashboard();

  // Transform the data into the format expected by StatsMultiDisplay
  const transformedData = stats.mostDownloadedRecords?.slice(0, pageSize).map((record, index) => ({
    name: record.title,
    value: record.downloads,
    percentage: record.percentage,
    link: `/records/${record.id}`,
    itemStyle: {
      color: SERIES_COLORS[index % SERIES_COLORS.length][1]
    }
  })) || [];

  const remainingItems = stats.mostDownloadedRecords?.slice(pageSize) || [];
  const otherData = remainingItems.length > 0 ? remainingItems.reduce((acc, record) => {
    acc.value += record.downloads;
    acc.percentage += record.percentage;
    return acc;
  }, {
    id: "other",
    name: "Other",
    value: 0,
    percentage: 0,
    link: null,
    itemStyle: {
      color: SERIES_COLORS[7][1] // Use grey color for "Other"
    }
  }) : null;

  const rowsWithLinks = [
    ...transformedData,
    ...(otherData ? [otherData] : [])
  ].map(({ name, value, percentage, link }) => [
    null,
    link ? <a href={link} target="_blank" rel="noopener noreferrer">{name}</a> : name,
    `${formatNumber(value, 'compact')}`
  ]);

  const getChartOptions = () => {
    const options = {
      "list": {},
      "pie": {
        grid: {
          top: '7%',
          right: '5%',
          bottom: '5%',
          left: '2%',
          containLabel: true
        },
        tooltip: {
          trigger: "item",
          formatter: (params) => {
            return `<div>
              ${params.name}: ${formatNumber(params.value, 'compact')}
            </div>`;
          },
        },
        series: [
          {
            type: "pie",
            radius: ["20%", "70%"],
            data: [...transformedData, otherData],
            label: {
              show: true,
              fontSize: 14
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: "rgba(0, 0, 0, 0.5)",
              },
            },
          },
        ],
      },
      "bar": {
        grid: {
          top: '7%',
          right: '5%',
          bottom: '5%',
          left: '2%',
          containLabel: true
        },
        tooltip: {
          trigger: "item",
          formatter: (params) => {
            return `<div>
              ${params.name}: ${formatNumber(params.value, 'compact')}
            </div>`;
          },
        },
        yAxis: {
          type: "category",
          data: [...transformedData.map(({ name }) => name), ...(otherData ? [otherData.name] : [])],
          axisTick: {show: false},
          axisLabel: {
            show: false,
          },
        },
        xAxis: {
          type: "value",
          axisLabel: {
            fontSize: 14,
            formatter: (value) => formatNumber(value, 'compact')
          },
        },
        series: [
          {
            type: "bar",
            barWidth: '90%',
            data: [...transformedData, ...(otherData ? [otherData] : [])].map((item) => {
              const maxValue = Math.max(...[...transformedData, ...(otherData ? [otherData] : [])].map(d => d.value));
              return {
                value: item.value,
                percentage: item.percentage,
                itemStyle: {
                  color: item.itemStyle.color
                },
                label: {
                  show: true,
                  formatter: "{b}",
                  fontSize: 14,
                  position: item.value < maxValue * 0.3 ? 'right' : 'inside',
                  color: item.value < maxValue * 0.3 ? item.itemStyle.color : '#fff',
                  align: item.value < maxValue * 0.3 ? 'left' : 'center',
                  verticalAlign: 'middle'
                }
              };
            }),
          },
        ],
      },
    };

    // Filter chart options based on available_views
    return Object.fromEntries(
      Object.entries(options).filter(([key]) => available_views.includes(key))
    );
  };

  return (
    <StatsMultiDisplay
      title={title || i18next.t('Most Downloaded Records')}
      icon={icon}
      label="downloaded_records"
      headers={headers}
      rows={rowsWithLinks}
      chartOptions={getChartOptions()}
      defaultViewMode={default_view || available_views[0]}
      pageSize={pageSize}
      isLoading={isLoading}
      onEvents={{
        click: (params) => {
          if (params.data && params.data.id) {
            window.open(params.data.link, '_blank');
          }
        }
      }}
      {...otherProps}
    />
  );
};

MostDownloadedRecordsMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  pageSize: PropTypes.number,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { MostDownloadedRecordsMultiDisplay };