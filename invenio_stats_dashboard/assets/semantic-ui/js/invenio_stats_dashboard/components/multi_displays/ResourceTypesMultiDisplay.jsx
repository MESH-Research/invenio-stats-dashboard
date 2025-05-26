import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { formatNumber } from "../../utils/numbers";
import ReactECharts from "echarts-for-react";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS } from '../../constants';

const ResourceTypesMultiDisplay = ({
  title = i18next.t("Resource Types"),
  icon: labelIcon = "file",
  headers = [i18next.t("Work Type"), i18next.t("Works")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, dateRange } = useStatsDashboard();

  // Transform the data into the format expected by StatsMultiDisplay
  const transformedData = stats.resourceTypes?.slice(0, pageSize).map((type, index) => ({
    name: type.name,
    value: type.count,
    percentage: type.percentage,
    id: type.name.toLowerCase().replace(/\s+/g, '-'),
    itemStyle: {
      color: CHART_COLORS.secondary[index % CHART_COLORS.secondary.length][1]
    }
  })) || [];

  const remainingItems = stats.resourceTypes?.slice(pageSize) || [];
  const otherData = remainingItems.length > 0 ? remainingItems.reduce((acc, type) => {
    acc.value += type.count;
    acc.percentage += type.percentage;
    return acc;
  }, {
    id: "other",
    name: "Other",
    value: 0,
    percentage: 0,
    itemStyle: {
      color: CHART_COLORS.secondary[CHART_COLORS.secondary.length - 1][1] // Use last color for "Other"
    }
  }) : null;

  const rowsWithLinks = [
    ...transformedData,
    ...(otherData ? [otherData] : [])
  ].map(({ name, value, percentage, id }) => [
    null,
    <a
      href={`/search?q=metadata.resource_type.id:${id}`}
      target="_blank"
      rel="noopener noreferrer"
    >
      {name}
    </a>,
    `${formatNumber(value, 'compact')} (${percentage}%)`,
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
              ${params.name}: ${formatNumber(params.value, 'compact')} (${params.data.percentage}%)
            </div>`;
          },
        },
        series: [
          {
            type: "pie",
            radius: ["30%", "70%"],
            data: [...transformedData, otherData],
            spacing: 2,
            itemStyle: {
              borderWidth: 2,
              borderColor: '#fff'
            },
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
              ${params.name}: ${formatNumber(params.value, 'compact')} (${params.data.percentage}%)
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
            data: [...transformedData, ...(otherData ? [otherData] : [])].map((item, index) => {
              const maxValue = Math.max(...[...transformedData, ...(otherData ? [otherData] : [])].map(d => d.value));
              return {
                value: item.value,
                percentage: item.percentage,
                id: item.id,
                itemStyle: {
                  color: CHART_COLORS.primary[index % CHART_COLORS.primary.length][1]
                },
                label: {
                  show: true,
                  formatter: "{b}",
                  fontSize: 14,
                  position: item.value < maxValue * 0.3 ? 'right' : 'inside',
                  color: item.value < maxValue * 0.3 ? CHART_COLORS.primary[index % CHART_COLORS.primary.length][1] : '#fff',
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
      title={title}
      icon={labelIcon}
      label={"resource-types"}
      headers={headers}
      rows={rowsWithLinks}
      chartOptions={getChartOptions()}
      defaultViewMode={default_view}
      onEvents={{
        click: (params) => {
          if (params.data && params.data.id) {
            window.open(`/search?q=metadata.resource_type.id:${params.data.id}`, '_blank');
          }
        }
      }}
      {...otherProps}
    />
  );
};

ResourceTypesMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { ResourceTypesMultiDisplay };