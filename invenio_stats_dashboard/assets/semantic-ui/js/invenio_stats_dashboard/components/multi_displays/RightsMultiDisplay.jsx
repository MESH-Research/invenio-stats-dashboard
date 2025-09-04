import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { formatNumber } from "../../utils/numbers";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS, RECORD_START_BASES } from '../../constants';
import { filterSeriesArrayByDate } from "../../utils";
import { transformMultiDisplayData, assembleMultiDisplayRows } from "../../utils/multiDisplayHelpers";

const RightsMultiDisplay = ({
  title = i18next.t("Rights"),
  icon: labelIcon = "copyright",
  headers = [i18next.t("Rights"), i18next.t("Works")],
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

  const rightsData = seriesCategoryMap[recordStartBasis]?.rights?.records;
  const rawRights = filterSeriesArrayByDate(rightsData, dateRange, true);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawRights,
    pageSize,
    'metadata.rights.id',
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
          axisLine: {
            show: false
          },
          axisTick: {
            show: false
          },
          axisLabel: {
            fontSize: 12
          }
        },
        xAxis: {
          type: "value",
          axisLine: {
            show: false
          },
          axisTick: {
            show: false
          },
          axisLabel: {
            fontSize: 12
          }
        },
        series: [
          {
            type: "bar",
            data: [...transformedData, ...(otherData ? [otherData] : [])],
            itemStyle: {
              color: (params) => {
                return CHART_COLORS.secondary[params.dataIndex % CHART_COLORS.secondary.length];
              }
            },
            label: {
              show: true,
              position: "right",
              formatter: (params) => {
                return formatNumber(params.value, 'compact');
              }
            }
          },
        ],
      },
    };

    return options[default_view] || options["pie"];
  };

  const chartOptions = getChartOptions();

  return (
    <StatsMultiDisplay
      title={title}
      icon={labelIcon}
      headers={headers}
      default_view={default_view}
      available_views={available_views}
      pageSize={pageSize}
      totalCount={totalCount}
      chartOptions={chartOptions}
      rows={rowsWithLinks}
      label={"rights"}
      isLoading={isLoading}
      hasData={hasData}
      {...otherProps}
    />
  );
};

RightsMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  default_view: PropTypes.string,
  pageSize: PropTypes.number,
  available_views: PropTypes.array,
};

export { RightsMultiDisplay };
