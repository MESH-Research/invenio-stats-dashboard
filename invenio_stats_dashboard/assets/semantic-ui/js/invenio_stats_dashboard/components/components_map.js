import {
  // Charts
  ContentStatsChart,
  ContentStatsChartCumulative,
  TrafficStatsChart,
  TrafficStatsChartCumulative,

  // Controls
  DateRangeSelector,
  GranularitySelector,
  ReportSelector,

  // Shared Components
  StatsChart,
  StatsTable,
  SingleStatBox,
  StatsPopup,

  // Single Stats
  SingleStatRecordCount,
  SingleStatRecordCountCumulative,
  SingleStatUploaders,
  SingleStatUploadersCumulative,
  SingleStatTraffic,
  SingleStatDataVolume,
  SingleStatDataVolumeCumulative,
  SingleStatDownloads,
  SingleStatViews,

  // Tables
  MostDownloadedRecordsTable,
  MostViewedRecordsTable,
  TopCountriesTable,
  TopReferrerDomainsTable,
  AccessRightsTable,
  LicensesTable,
  AffiliationsTable,
  FundersTable,
  SubjectsTable,
  LanguagesTable,

  // Maps
  StatsMap,

  // Multi Displays
  ResourceTypesMultiDisplay,
} from './index';

import { AccessRightsMultiDisplay } from "./multi_displays/AccessRightsMultiDisplay";
import { LicensesMultiDisplay } from "./multi_displays/LicensesMultiDisplay";
import { AffiliationsMultiDisplay } from "./multi_displays/AffiliationsMultiDisplay";
import { FundersMultiDisplay } from "./multi_displays/FundersMultiDisplay";
import { TopCountriesMultiDisplay } from "./multi_displays/TopCountriesMultiDisplay";
import { TopReferrerDomainsMultiDisplay } from "./multi_displays/TopReferrerDomainsMultiDisplay";
import { MostDownloadedRecordsMultiDisplay } from "./multi_displays/MostDownloadedRecordsMultiDisplay";
import { MostViewedRecordsMultiDisplay } from "./multi_displays/MostViewedRecordsMultiDisplay";

export const componentsMap = {
  // Charts
  'ContentStatsChart': ContentStatsChart,
  'ContentStatsChartCumulative': ContentStatsChartCumulative,
  'TrafficStatsChart': TrafficStatsChart,
  'TrafficStatsChartCumulative': TrafficStatsChartCumulative,

  // Controls
  'DateRangeSelector': DateRangeSelector,
  'GranularitySelector': GranularitySelector,
  'ReportSelector': ReportSelector,

  // Shared Components
  'StatsChart': StatsChart,
  'StatsTable': StatsTable,
  'SingleStatBox': SingleStatBox,
  'StatsPopup': StatsPopup,

  // Single Stats
  'SingleStatRecordCount': SingleStatRecordCount,
  'SingleStatRecordCountCumulative': SingleStatRecordCountCumulative,
  'SingleStatUploaders': SingleStatUploaders,
  'SingleStatUploadersCumulative': SingleStatUploadersCumulative,
  'SingleStatTraffic': SingleStatTraffic,
  'SingleStatDataVolume': SingleStatDataVolume,
  'SingleStatDataVolumeCumulative': SingleStatDataVolumeCumulative,
  'SingleStatDownloads': SingleStatDownloads,
  'SingleStatViews': SingleStatViews,

  // Tables
  'MostDownloadedRecordsTable': MostDownloadedRecordsTable,
  'MostViewedRecordsTable': MostViewedRecordsTable,
  'TopCountriesTable': TopCountriesTable,
  'TopReferrerDomainsTable': TopReferrerDomainsTable,
  'AccessRightsTable': AccessRightsTable,
  'LicensesTable': LicensesTable,
  'AffiliationsTable': AffiliationsTable,
  'FundersTable': FundersTable,
  'SubjectsTable': SubjectsTable,
  'LanguagesTable': LanguagesTable,

  // Maps
  'StatsMap': StatsMap,

  // Multi Displays
  'ResourceTypesMultiDisplay': ResourceTypesMultiDisplay,
  'AccessRightsMultiDisplay': AccessRightsMultiDisplay,
  'LicensesMultiDisplay': LicensesMultiDisplay,
  'AffiliationsMultiDisplay': AffiliationsMultiDisplay,
  'FundersMultiDisplay': FundersMultiDisplay,
  'TopCountriesMultiDisplay': TopCountriesMultiDisplay,
  'TopReferrerDomainsMultiDisplay': TopReferrerDomainsMultiDisplay,
  'MostDownloadedRecordsMultiDisplay': MostDownloadedRecordsMultiDisplay,
  'MostViewedRecordsMultiDisplay': MostViewedRecordsMultiDisplay,
};
