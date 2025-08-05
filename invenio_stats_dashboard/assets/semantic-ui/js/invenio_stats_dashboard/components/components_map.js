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
  SingleStatDownloadsCumulative,
  SingleStatViews,
  SingleStatViewsCumulative,
  SingleStatTrafficCumulative,

  // Maps
  StatsMap,

  // Multi Displays
  ResourceTypesMultiDisplay,
  SubjectsMultiDisplay,
} from './index';

import { AccessStatusMultiDisplay } from "./multi_displays/AccessStatusMultiDisplay";
import { LicensesMultiDisplay } from "./multi_displays/LicensesMultiDisplay";
import { AffiliationsMultiDisplay } from "./multi_displays/AffiliationsMultiDisplay";
import { FundersMultiDisplay } from "./multi_displays/FundersMultiDisplay";
import { TopCountriesMultiDisplay } from "./multi_displays/CountriesMultiDisplay";
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
  'SingleStatDownloadsCumulative': SingleStatDownloadsCumulative,
  'SingleStatViews': SingleStatViews,
  'SingleStatViewsCumulative': SingleStatViewsCumulative,
  'SingleStatTrafficCumulative': SingleStatTrafficCumulative,

  // Maps
  'StatsMap': StatsMap,

  // Multi Displays
  'ResourceTypesMultiDisplay': ResourceTypesMultiDisplay,
  'SubjectsMultiDisplay': SubjectsMultiDisplay,
  'AccessStatusMultiDisplay': AccessStatusMultiDisplay,
  'LicensesMultiDisplay': LicensesMultiDisplay,
  'AffiliationsMultiDisplay': AffiliationsMultiDisplay,
  'FundersMultiDisplay': FundersMultiDisplay,
  'TopCountriesMultiDisplay': TopCountriesMultiDisplay,
  'TopReferrerDomainsMultiDisplay': TopReferrerDomainsMultiDisplay,
  'MostDownloadedRecordsMultiDisplay': MostDownloadedRecordsMultiDisplay,
  'MostViewedRecordsMultiDisplay': MostViewedRecordsMultiDisplay,
};
