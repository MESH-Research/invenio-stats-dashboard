import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import { Container, Grid, Header, Icon, Popup, Button, ButtonGroup, Dropdown } from "semantic-ui-react";
import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import { formatNumber } from "./utils/numbers";
import { SingleStatViews } from "./components/single_stats/SingleStatViews";
import { SingleStatDownloads } from "./components/single_stats/SingleStatDownloads";
import { SingleStatDataVolume } from "./components/single_stats/SingleStatDataVolume";
import { SingleStatTraffic } from "./components/single_stats/SingleStatTraffic";
import { SingleStatUploaders } from "./components/single_stats/SingleStatUploaders";
import { SingleStatRecordCount } from "./components/single_stats/SingleStatRecordCount";
import { StatsChart } from "./components/shared_components/StatsChart";
import { DateRangeSelector } from "./components/shared_components/DateRangeSelector";
import { MostViewedRecordsTable, MostDownloadedRecordsTable } from "./components";
import { testRecordData } from "./testData";
import {
  Button as AriaButton,
  CalendarCell,
  CalendarGrid,
  DateInput,
  DateRangePicker,
  DateSegment,
  Dialog,
  Group,
  Heading,
  Label,
  Popover,
  RangeCalendar
} from 'react-aria-components';
import { today, getLocalTimeZone } from "@internationalized/date";

const StatsDashboard = ({ config, stats, title, description, maxHistoryYears = 15 }) => {
  const all_versions = {
    unique_views: 1000000,
    unique_downloads: 1000000,
    data_volume: 1000000,
    total_uploads: 1000000,
    total_users: 1000000,
    total_communities: 1000000,
    total_languages: 1000000,
  };
  const [totalViews, setTotalViews] = useState(all_versions.unique_views);
  const [totalDownloads, setTotalDownloads] = useState(all_versions.unique_downloads);
  const [totalDataVolume, setTotalDataVolume] = useState(all_versions.data_volume);
  const [totalUploads, setTotalUploads] = useState(all_versions.total_uploads);
  const [totalUsers, setTotalUsers] = useState(all_versions.total_users);
  const [totalCommunities, setTotalCommunities] = useState(all_versions.total_communities);
  const [totalLanguages, setTotalLanguages] = useState(all_versions.total_languages);
  const this_version = all_versions;

  const binary_sizes = !config?.APP_RDM_DISPLAY_DECIMAL_FILE_SIZES;

  const [showMore, setShowMore] = useState(false);
  const [chartData, setChartData] = useState([]);
  const [granularity, setGranularity] = useState("day");

  const [dateRange, setDateRange] = useState({
    start: today(getLocalTimeZone()).subtract({ days: 30 }),
    end: today(getLocalTimeZone())
  });

  const handleGranularityChange = (newGranularity) => {
    setGranularity(newGranularity);
  };

  useEffect(() => {
    // Transform stats data into chart format
    const transformData = () => {
      const views = {
        name: "Views",
        data: stats.views?.map(point => [point.date, point.value]) || []
      };
      const downloads = {
        name: "Downloads",
        data: stats.downloads?.map(point => [point.date, point.value]) || []
      };
      const traffic = {
        name: "Traffic",
        data: stats.traffic?.map(point => [point.date, point.value]) || []
      };

      return [views, downloads, traffic].filter(series => series.data.length > 0);
    };

    setChartData(transformData());
  }, [stats]);

  return (
    <Container fluid className="stats-dashboard" role="main" aria-label={title || i18next.t("Stats Dashboard")}>
      <Container>
        <Grid>
          <Grid.Row>
            <Grid.Column width={16}>
              <Header as="h2" className="stats-dashboard-header">
                {title || i18next.t("Stats Dashboard")}
                {description && (
                  <Popup
                    trigger={
                      <Button
                        icon="info circle"
                        aria-label={i18next.t("More information about statistics")}
                        className="stats-info-button"
                      />
                    }
                    content={description}
                    position="right center"
                    aria-label={i18next.t("Statistics description")}
                  />
                )}
              </Header>
            </Grid.Column>
          </Grid.Row>

          <Grid.Row>
            <Grid.Column width={16}>
              <DateRangeSelector
                dateRange={dateRange}
                onDateRangeChange={setDateRange}
                granularity={granularity}
                onGranularityChange={handleGranularityChange}
                maxHistoryYears={maxHistoryYears}
              />
            </Grid.Column>
          </Grid.Row>

          <Grid.Row>
            <Grid.Column width={16}>
              <Grid>
                <Grid.Row columns={3}>
                  <Grid.Column>
                    <SingleStatViews
                      value={stats.views?.reduce((sum, point) => sum + point.value, 0) || 0}
                      dateRange={dateRange}
                      granularity={granularity}
                    />
                  </Grid.Column>
                  <Grid.Column>
                    <SingleStatDownloads
                      value={stats.downloads?.reduce((sum, point) => sum + point.value, 0) || 0}
                      dateRange={dateRange}
                      granularity={granularity}
                    />
                  </Grid.Column>
                  <Grid.Column>
                    <SingleStatDataVolume
                      value={stats.dataVolume?.reduce((sum, point) => sum + point.value, 0) || 0}
                      dateRange={dateRange}
                      granularity={granularity}
                    />
                  </Grid.Column>
                </Grid.Row>

                {showMore && (
                  <Grid.Row columns={3}>
                    <Grid.Column>
                      <SingleStatTraffic
                        value={stats.traffic?.reduce((sum, point) => sum + point.value, 0) || 0}
                        dateRange={dateRange}
                        granularity={granularity}
                      />
                    </Grid.Column>
                    <Grid.Column>
                      <SingleStatUploaders
                        value={stats.uploaders?.reduce((sum, point) => sum + point.value, 0) || 0}
                        dateRange={dateRange}
                        granularity={granularity}
                      />
                    </Grid.Column>
                    <Grid.Column>
                      <SingleStatRecordCount
                        value={stats.recordCount?.reduce((sum, point) => sum + point.value, 0) || 0}
                        dateRange={dateRange}
                        granularity={granularity}
                      />
                    </Grid.Column>
                  </Grid.Row>
                )}

                <Grid.Row>
                  <Grid.Column width={16}>
                    <div className="stats-dashboard-more">
                      <Button
                        as="a"
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          setShowMore(!showMore);
                        }}
                        aria-expanded={showMore}
                        aria-controls="additional-stats"
                      >
                        {showMore
                          ? i18next.t("Show less details")
                          : i18next.t("Show more details")}
                      </Button>
                    </div>
                  </Grid.Column>
                </Grid.Row>

                {chartData.length > 0 && (
                  <Grid.Row>
                    <StatsChart
                      data={chartData}
                      title={null}
                      xAxisLabel={i18next.t("Date")}
                      yAxisLabel={i18next.t("Count")}
                      stacked={false}
                      areaStyle={true}
                      granularity={granularity}
                      dateRange={dateRange}
                      classnames="sixteen wide column"
                    />
                  </Grid.Row>
                )}

                <Grid.Row columns={2} id="additional-stats">
                  <Grid.Column width={8}>
                    <MostViewedRecordsTable
                      headers={["Record", "Views"]}
                      rows={testRecordData.mostViewed}
                      dateRange={dateRange}
                      granularity={granularity}
                    />
                  </Grid.Column>
                  <Grid.Column width={8}>
                    <MostDownloadedRecordsTable
                      headers={["Record", "Downloads"]}
                      rows={testRecordData.mostDownloaded}
                      dateRange={dateRange}
                      granularity={granularity}
                    />
                  </Grid.Column>
                </Grid.Row>
              </Grid>
            </Grid.Column>
          </Grid.Row>
        </Grid>
      </Container>
    </Container>
  );
};

StatsDashboard.propTypes = {
  config: PropTypes.object.isRequired,
  stats: PropTypes.shape({
    views: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    downloads: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    dataVolume: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    traffic: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    uploaders: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
    recordCount: PropTypes.arrayOf(
      PropTypes.shape({
        date: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      })
    ),
  }).isRequired,
  title: PropTypes.string,
  description: PropTypes.string,
  maxHistoryYears: PropTypes.number,
};

export { StatsDashboard };
