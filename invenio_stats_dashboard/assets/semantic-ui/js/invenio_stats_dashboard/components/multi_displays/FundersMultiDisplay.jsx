import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { formatNumber } from "../../utils/numbers";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS, RECORD_START_BASES } from '../../constants';
import { filterSeriesArrayByDate } from "../../utils";
import { transformMultiDisplayData, assembleMultiDisplayRows } from "../../utils/multiDisplayHelpers";

const FundersMultiDisplay = ({
  title = i18next.t("Funders"),
  icon: labelIcon = "money bill",
  headers = [i18next.t("Funder"), i18next.t("Works")],
  default_view = "pie",
  pageSize = 10,
  available_views = ["pie", "bar", "list"],
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange, isLoading } = useStatsDashboard();

  const seriesCategoryMap = {
    [RECORD_START_BASES.ADDED]: stats?.recordSnapshotDataAdded,
    [RECORD_START_BASES.CREATED]: stats?.recordSnapshotDataCreated,
    [RECORD_START_BASES.PUBLISHED]: stats?.recordSnapshotDataPublished,
  };

  const fundersData = seriesCategoryMap[recordStartBasis]?.funders?.records;
  const rawFunders = filterSeriesArrayByDate(fundersData, dateRange, true);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawFunders,
    pageSize,
    'metadata.funding.funder',
    CHART_COLORS.secondary
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

  // Check if there's any data to display
  const hasData = !isLoading && (transformedData.length > 0 || (otherData && otherData.value > 0));

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
            data: [...transformedData, ...(otherData ? [otherData] : [])],
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
                itemStyle: item.itemStyle,
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
      defaultViewMode={default_view}
      isLoading={isLoading}
      hasData={hasData}
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