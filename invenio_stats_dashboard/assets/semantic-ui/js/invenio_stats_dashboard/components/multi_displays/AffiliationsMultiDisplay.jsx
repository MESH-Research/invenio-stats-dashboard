import React from "react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { StatsMultiDisplay } from "../shared_components/StatsMultiDisplay";
import { PropTypes } from "prop-types";
import { formatNumber } from "../../utils/numbers";
import { useStatsDashboard } from "../../context/StatsDashboardContext";
import { CHART_COLORS, RECORD_START_BASES } from '../../constants';
import { filterSeriesArrayByDate } from "../../utils";
import { transformMultiDisplayData, assembleMultiDisplayRows } from "../../utils/multiDisplayHelpers";

const AffiliationsMultiDisplay = ({
  title = i18next.t("Affiliations"),
  icon: labelIcon = "university",
  headers = [i18next.t("Affiliation"), i18next.t("Works")],
  default_view,
  pageSize = 10,
  available_views = ["list", "pie", "bar"],
  ...otherProps
}) => {
  const { stats, recordStartBasis, dateRange } = useStatsDashboard();

  const seriesCategoryMap = {
    [RECORD_START_BASES.ADDED]: stats?.recordSnapshotDataAdded,
    [RECORD_START_BASES.CREATED]: stats?.recordSnapshotDataCreated,
    [RECORD_START_BASES.PUBLISHED]: stats?.recordSnapshotDataPublished,
  };

  const affiliationsData = seriesCategoryMap[recordStartBasis]?.affiliations?.records;
  const rawAffiliations = filterSeriesArrayByDate(affiliationsData, dateRange, true);

  const { transformedData, otherData, totalCount } = transformMultiDisplayData(
    rawAffiliations,
    pageSize,
    'metadata.affiliations.affiliation',
    CHART_COLORS.secondary
  );
  const rowsWithLinks = assembleMultiDisplayRows(transformedData, otherData);

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
      label={"affiliations"}
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

AffiliationsMultiDisplay.propTypes = {
  title: PropTypes.string,
  icon: PropTypes.string,
  headers: PropTypes.array,
  rows: PropTypes.array,
  default_view: PropTypes.string,
  available_views: PropTypes.arrayOf(PropTypes.string),
};

export { AffiliationsMultiDisplay };