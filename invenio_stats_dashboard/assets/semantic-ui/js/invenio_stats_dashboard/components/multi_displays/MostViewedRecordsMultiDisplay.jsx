import React from 'react';
import PropTypes from 'prop-types';
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from '../shared_components/StatsMultiDisplay';
import { formatNumber } from '../../utils';
import { useStatsDashboard } from '../../context/StatsDashboardContext';
import { CHART_COLORS } from '../../constants';

const MostViewedRecordsMultiDisplay = ({
  title = i18next.t("Most Viewed Works"),
  pageSize = 10,
  available_views = ["list"],
  default_view = "list",
}) => {
  const { stats, dateRange, isLoading } = useStatsDashboard();

  // Transform the data into the format expected by StatsMultiDisplay
  const transformedData = stats.mostViewedRecords?.slice(0, pageSize).map((record, index) => ({
    name: record.title,
    value: record.views,
    percentage: record.percentage,
    link: `/records/${record.id}`,
    itemStyle: {
      color: CHART_COLORS.secondary[index % CHART_COLORS.secondary.length][1]
    }
  })) || [];

  const remainingItems = stats.mostViewedRecords?.slice(pageSize) || [];
  const otherData = remainingItems.length > 0 ? remainingItems.reduce((acc, record) => {
    acc.value += record.views;
    acc.percentage += record.percentage;
    return acc;
  }, {
    id: "other",
    name: "Other",
    value: 0,
    percentage: 0,
    link: null,
    itemStyle: {
      color: CHART_COLORS.secondary[CHART_COLORS.secondary.length - 1][1] // Use last color for "Other"
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
            radius: ["30%", "70%"],
            data: [...transformedData, otherData],
            spacing: 2,
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
            itemStyle: {
              borderWidth: 2,
              borderColor: '#fff'
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
      title={title || i18next.t('Most Viewed Records')}
      icon="eye"
      label="viewed_records"
      headers={[i18next.t("Record"), i18next.t("Views")]}
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
    />
  );
};

MostViewedRecordsMultiDisplay.propTypes = {
  title: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.arrayOf(PropTypes.string),
  default_view: PropTypes.string,
};

export { MostViewedRecordsMultiDisplay };