import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { formatNumber } from "../../utils/numbers";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS } from '../../constants';

const AccessRightsMultiDisplay = ({
  title = i18next.t("Access Rights"),
  icon: labelIcon = "lock",
  headers = [i18next.t("Access Right"), i18next.t("Works")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, dateRange } = useStatsDashboard();

  // Helper function to extract access rights from the new data structure
  const extractAccessRights = () => {
    // Try to get access rights from record snapshot data
    if (stats.recordSnapshotDataAdded && stats.recordSnapshotDataAdded.accessRights) {
      const accessRightsData = stats.recordSnapshotDataAdded.accessRights;
      return Object.entries(accessRightsData).map(([id, data]) => ({
        name: data.records[2] || id, // Use label if available, otherwise use id
        count: data.records[1] || 0, // Use the count value
        percentage: 0, // Calculate percentage later
        id: id,
      }));
    }

    // Fallback to empty array if no data available
    return [];
  };

  const rawAccessRights = extractAccessRights();

  // Calculate percentages
  const totalCount = rawAccessRights.reduce((sum, right) => sum + right.count, 0);
  const accessRightsWithPercentages = rawAccessRights.map(right => ({
    ...right,
    percentage: totalCount > 0 ? Math.round((right.count / totalCount) * 100) : 0,
  }));

  // Transform the data into the format expected by StatsMultiDisplay
  const transformedData = accessRightsWithPercentages.slice(0, pageSize).map((right, index) => ({
    name: right.name,
    value: right.count,
    percentage: right.percentage,
    id: right.id,
    link: `/search?q=metadata.access_right.id:${right.id}`,
    itemStyle: {
      color: CHART_COLORS.secondary[index % CHART_COLORS.secondary.length][1]
    }
  }));

  const remainingItems = accessRightsWithPercentages.slice(pageSize) || [];
  const otherData = remainingItems.length > 0 ? remainingItems.reduce((acc, right) => {
    acc.value += right.count;
    acc.percentage += right.percentage;
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
  ].map(({ name, value, percentage, link }) => [
    null,
    link ? <a href={link} target="_blank" rel="noopener noreferrer">{name}</a> : name,
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
      label={"access-rights"}
      headers={headers}
      rows={rowsWithLinks}
      chartOptions={getChartOptions()}
      defaultViewMode={default_view}
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

AccessRightsMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { AccessRightsMultiDisplay };