// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

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
  StatsMultiDisplay,

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
  AccessStatusesMultiDisplay,
  RightsMultiDisplay,
  AffiliationsMultiDisplay,
  FundersMultiDisplay,
  TopCountriesMultiDisplay,
  TopReferrersMultiDisplay,
  MostDownloadedRecordsMultiDisplay,
  MostViewedRecordsMultiDisplay,
  PeriodicalsMultiDisplay,
  PublishersMultiDisplay,
  TopLanguagesMultiDisplay,
  FileTypesMultiDisplay,

  // Multi Displays Delta
  ResourceTypesMultiDisplayDelta,
  SubjectsMultiDisplayDelta,
  AccessStatusesMultiDisplayDelta,
  RightsMultiDisplayDelta,
  AffiliationsMultiDisplayDelta,
  FundersMultiDisplayDelta,
  CountriesMultiDisplayDelta,
  PeriodicalsMultiDisplayDelta,
  PublishersMultiDisplayDelta,
  LanguagesMultiDisplayDelta,
  FileTypesMultiDisplayDelta,

  // Multi Displays Views (snapshot)
  SubjectsMultiDisplayViews,
  ResourceTypesMultiDisplayViews,
  AccessStatusesMultiDisplayViews,
  RightsMultiDisplayViews,
  AffiliationsMultiDisplayViews,
  FundersMultiDisplayViews,
  PeriodicalsMultiDisplayViews,
  PublishersMultiDisplayViews,
  LanguagesMultiDisplayViews,
  FileTypesMultiDisplayViews,

  // Multi Displays Views Delta
  SubjectsMultiDisplayViewsDelta,
  ResourceTypesMultiDisplayViewsDelta,
  AccessStatusesMultiDisplayViewsDelta,
  RightsMultiDisplayViewsDelta,
  AffiliationsMultiDisplayViewsDelta,
  FundersMultiDisplayViewsDelta,
  PeriodicalsMultiDisplayViewsDelta,
  PublishersMultiDisplayViewsDelta,
  LanguagesMultiDisplayViewsDelta,
  FileTypesMultiDisplayViewsDelta,

  // Multi Displays Downloads (snapshot)
  SubjectsMultiDisplayDownloads,
  ResourceTypesMultiDisplayDownloads,
  AccessStatusesMultiDisplayDownloads,
  RightsMultiDisplayDownloads,
  AffiliationsMultiDisplayDownloads,
  FundersMultiDisplayDownloads,
  PeriodicalsMultiDisplayDownloads,
  PublishersMultiDisplayDownloads,
  LanguagesMultiDisplayDownloads,
  FileTypesMultiDisplayDownloads,

  // Multi Displays Downloads Delta
  SubjectsMultiDisplayDownloadsDelta,
  ResourceTypesMultiDisplayDownloadsDelta,
  AccessStatusesMultiDisplayDownloadsDelta,
  RightsMultiDisplayDownloadsDelta,
  AffiliationsMultiDisplayDownloadsDelta,
  FundersMultiDisplayDownloadsDelta,
  PeriodicalsMultiDisplayDownloadsDelta,
  PublishersMultiDisplayDownloadsDelta,
  LanguagesMultiDisplayDownloadsDelta,
  FileTypesMultiDisplayDownloadsDelta,
} from './index';

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
  'StatsMultiDisplay': StatsMultiDisplay,

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
  'AccessStatusesMultiDisplay': AccessStatusesMultiDisplay,
  'RightsMultiDisplay': RightsMultiDisplay,
  'AffiliationsMultiDisplay': AffiliationsMultiDisplay,
  'FundersMultiDisplay': FundersMultiDisplay,
  'TopCountriesMultiDisplay': TopCountriesMultiDisplay,
  'TopReferrersMultiDisplay': TopReferrersMultiDisplay,
  'MostDownloadedRecordsMultiDisplay': MostDownloadedRecordsMultiDisplay,
  'MostViewedRecordsMultiDisplay': MostViewedRecordsMultiDisplay,
  'PeriodicalsMultiDisplay': PeriodicalsMultiDisplay,
  'PublishersMultiDisplay': PublishersMultiDisplay,
  'TopLanguagesMultiDisplay': TopLanguagesMultiDisplay,
  'FileTypesMultiDisplay': FileTypesMultiDisplay,

  // Multi Displays Delta
  'ResourceTypesMultiDisplayDelta': ResourceTypesMultiDisplayDelta,
  'SubjectsMultiDisplayDelta': SubjectsMultiDisplayDelta,
  'AccessStatusesMultiDisplayDelta': AccessStatusesMultiDisplayDelta,
  'RightsMultiDisplayDelta': RightsMultiDisplayDelta,
  'AffiliationsMultiDisplayDelta': AffiliationsMultiDisplayDelta,
  'FundersMultiDisplayDelta': FundersMultiDisplayDelta,
  'CountriesMultiDisplayDelta': CountriesMultiDisplayDelta,
  'PeriodicalsMultiDisplayDelta': PeriodicalsMultiDisplayDelta,
  'PublishersMultiDisplayDelta': PublishersMultiDisplayDelta,
  'LanguagesMultiDisplayDelta': LanguagesMultiDisplayDelta,
  'FileTypesMultiDisplayDelta': FileTypesMultiDisplayDelta,

  // Multi Displays Views (snapshot)
  'SubjectsMultiDisplayViews': SubjectsMultiDisplayViews,
  'ResourceTypesMultiDisplayViews': ResourceTypesMultiDisplayViews,
  'AccessStatusesMultiDisplayViews': AccessStatusesMultiDisplayViews,
  'RightsMultiDisplayViews': RightsMultiDisplayViews,
  'AffiliationsMultiDisplayViews': AffiliationsMultiDisplayViews,
  'FundersMultiDisplayViews': FundersMultiDisplayViews,
  'PeriodicalsMultiDisplayViews': PeriodicalsMultiDisplayViews,
  'PublishersMultiDisplayViews': PublishersMultiDisplayViews,
  'LanguagesMultiDisplayViews': LanguagesMultiDisplayViews,
  'FileTypesMultiDisplayViews': FileTypesMultiDisplayViews,

  // Multi Displays Views Delta
  'SubjectsMultiDisplayViewsDelta': SubjectsMultiDisplayViewsDelta,
  'ResourceTypesMultiDisplayViewsDelta': ResourceTypesMultiDisplayViewsDelta,
  'AccessStatusesMultiDisplayViewsDelta': AccessStatusesMultiDisplayViewsDelta,
  'RightsMultiDisplayViewsDelta': RightsMultiDisplayViewsDelta,
  'AffiliationsMultiDisplayViewsDelta': AffiliationsMultiDisplayViewsDelta,
  'FundersMultiDisplayViewsDelta': FundersMultiDisplayViewsDelta,
  'PeriodicalsMultiDisplayViewsDelta': PeriodicalsMultiDisplayViewsDelta,
  'PublishersMultiDisplayViewsDelta': PublishersMultiDisplayViewsDelta,
  'LanguagesMultiDisplayViewsDelta': LanguagesMultiDisplayViewsDelta,
  'FileTypesMultiDisplayViewsDelta': FileTypesMultiDisplayViewsDelta,

  // Multi Displays Downloads (snapshot)
  'SubjectsMultiDisplayDownloads': SubjectsMultiDisplayDownloads,
  'ResourceTypesMultiDisplayDownloads': ResourceTypesMultiDisplayDownloads,
  'AccessStatusesMultiDisplayDownloads': AccessStatusesMultiDisplayDownloads,
  'RightsMultiDisplayDownloads': RightsMultiDisplayDownloads,
  'AffiliationsMultiDisplayDownloads': AffiliationsMultiDisplayDownloads,
  'FundersMultiDisplayDownloads': FundersMultiDisplayDownloads,
  'PeriodicalsMultiDisplayDownloads': PeriodicalsMultiDisplayDownloads,
  'PublishersMultiDisplayDownloads': PublishersMultiDisplayDownloads,
  'LanguagesMultiDisplayDownloads': LanguagesMultiDisplayDownloads,
  'FileTypesMultiDisplayDownloads': FileTypesMultiDisplayDownloads,

  // Multi Displays Downloads Delta
  'SubjectsMultiDisplayDownloadsDelta': SubjectsMultiDisplayDownloadsDelta,
  'ResourceTypesMultiDisplayDownloadsDelta': ResourceTypesMultiDisplayDownloadsDelta,
  'AccessStatusesMultiDisplayDownloadsDelta': AccessStatusesMultiDisplayDownloadsDelta,
  'RightsMultiDisplayDownloadsDelta': RightsMultiDisplayDownloadsDelta,
  'AffiliationsMultiDisplayDownloadsDelta': AffiliationsMultiDisplayDownloadsDelta,
  'FundersMultiDisplayDownloadsDelta': FundersMultiDisplayDownloadsDelta,
  'PeriodicalsMultiDisplayDownloadsDelta': PeriodicalsMultiDisplayDownloadsDelta,
  'PublishersMultiDisplayDownloadsDelta': PublishersMultiDisplayDownloadsDelta,
  'LanguagesMultiDisplayDownloadsDelta': LanguagesMultiDisplayDownloadsDelta,
  'FileTypesMultiDisplayDownloadsDelta': FileTypesMultiDisplayDownloadsDelta,
};
