import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { formatNumber } from "../../utils/numbers";
import { useStatsDashboard } from "../../context/StatsDashboardContext";

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

const FundersMultiDisplay = ({
  title = i18next.t("Funders"),
  icon: labelIcon = "money bill",
  headers = [i18next.t("Funder"), i18next.t("Works")],
  default_view,
  pageSize = 10,
  available_views = ["list", "pie", "bar"],
  ...otherProps
}) => {
  const { stats } = useStatsDashboard();

  // Transform the data into the format expected by StatsMultiDisplay
  const transformedData = stats.funders?.slice(0, pageSize).map((funder, index) => ({
    name: funder.name,
    value: funder.count,
    percentage: funder.percentage,
    id: funder.name.toLowerCase().replace(/\s+/g, '-'),
    link: `/search?q=metadata.funding.funder:${funder.name.toLowerCase().replace(/\s+/g, '-')}`,
    itemStyle: {
      color: SERIES_COLORS[index % SERIES_COLORS.length][1]
    }
  })) || [];
  console.log('transformedData', transformedData);
  const remainingItems = stats.funders?.slice(pageSize) || [];
  const otherData = remainingItems.length > 0 ? remainingItems.reduce((acc, funder) => {
    acc.value += funder.count;
    acc.percentage += funder.percentage;
    return acc;
  }, {
    id: "other",
    name: "Other",
    value: 0,
    percentage: 0,
    itemStyle: {
      color: SERIES_COLORS[7][1] // Use grey color for "Other"
    }
  }) : null;
  console.log('otherData', otherData);
  console.log([...transformedData, ...(otherData ? [otherData] : [])]);

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
            data: [...transformedData, ...(otherData ? [otherData] : [])].map((item) => {
              const maxValue = Math.max(...[...transformedData, ...(otherData ? [otherData] : [])].map(d => d.value));
              return {
                value: item.value,
                percentage: item.percentage,
                id: item.id,
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
      title={title}
      icon={labelIcon}
      label={"funders"}
      headers={headers}
      rows={rowsWithLinks}
      chartOptions={getChartOptions()}
      defaultViewMode={default_view || available_views[0]}
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

FundersMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { FundersMultiDisplay };