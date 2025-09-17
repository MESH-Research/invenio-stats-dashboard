// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

/**
 * Mock data for the record delta API response.
 *
 * @type {Object}
 */
const sampleRecordDelta = {
  community_id: "5733deff-2f76-4f8c-bb99-8df48bdd725f",
  files: {
    added: { data_volume: 59117831.0, file_count: 2 },
    removed: { data_volume: 0.0, file_count: 0 },
  },
  parents: {
    added: { metadata_only: 0, with_files: 2 },
    removed: { metadata_only: 0, with_files: 0 },
  },
  period_end: "2025-05-30T23:59:59",
  period_start: "2025-05-30T00:00:00",
  records: {
    added: { metadata_only: 0, with_files: 2 },
    removed: { metadata_only: 0, with_files: 0 },
  },
  subcounts: {
    access_statuses: [
      {
        files: {
          added: { data_volume: 59117831.0, file_count: 2 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "open",
        label: "",
        parents: {
          added: { metadata_only: 0, with_files: 2 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 2 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
    ],
    affiliations_contributor: [],
    affiliations_creator: [
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "013v4ng57",
        label: "",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
    ],
    file_types: [
      {
        files: {
          added: { data_volume: 59117831.0, file_count: 2 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "pdf",
        label: "",
        parents: {
          added: { metadata_only: 0, with_files: 2 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 2 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
    ],
    funders: [],
    languages: [
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "eng",
        label: {"en": "English"},
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
    ],
    rights: [],
    periodicals: [],
    publishers: [
      {
        files: {
          added: { data_volume: 58659795.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "Apocryphile Press",
        label: "",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "Knowledge Commons",
        label: "",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
    ],
    resource_types: [
      {
        files: {
          added: { data_volume: 58659795.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "textDocument-bookSection",
        label: {"en": "Book Section"},
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "textDocument-journalArticle",
        label: {"en": "Journal Article"},
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
    ],
    subjects: [
      {
        files: {
          added: { data_volume: 58659795.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "http://id.worldcat.org/fast/973589",
        label: "Inklings (Group of writers)",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "http://id.worldcat.org/fast/855500",
        label: "Children of prisoners--Services for",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "http://id.worldcat.org/fast/997916",
        label: "Library science",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "http://id.worldcat.org/fast/2060143",
        label: "Mass incarceration",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "http://id.worldcat.org/fast/997974",
        label: "Library science--Standards",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "http://id.worldcat.org/fast/997987",
        label: "Library science literature",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
      {
        files: {
          added: { data_volume: 458036.0, file_count: 1 },
          removed: { data_volume: 0.0, file_count: 0 },
        },
        id: "http://id.worldcat.org/fast/995415",
        label: "Legal assistance to prisoners--U.S. states",
        parents: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
        records: {
          added: { metadata_only: 0, with_files: 1 },
          removed: { metadata_only: 0, with_files: 0 },
        },
      },
    ],
  },
  timestamp: "2025-06-05T18:45:58",
  updated_timestamp: "2025-06-05T18:45:58",
  uploaders: 1,
};

/**
 * Mock data for the record snapshot API response.
 *
 * @type {Array}
 */
const sampleRecordSnapshot = {
  community_id: "e64dee43-6bd2-4380-b4e8-2813315cb74e",
  snapshot_date: "2025-01-15",
  subcounts: {
    access_statuses: [
      {
        files: { data_volume: 0.0, file_count: 0 },
        id: "metadata-only",
        label: "",
        parents: { metadata_only: 1, with_files: 0 },
        records: { metadata_only: 1, with_files: 0 },
      },
    ],
    file_types: [],
    languages: [],
    rights: [],
    resource_types: [],
    affiliations: [],
    funders: [],
    periodicals: [],
    publishers: [],
    subjects: [],
  },
  timestamp: "2025-07-02T14:37:33",
  total_files: { data_volume: 0.0, file_count: 0 },
  total_parents: { metadata_only: 1, with_files: 0 },
  total_records: { metadata_only: 1, with_files: 0 },
  total_uploaders: 0,
  updated_timestamp: "2025-07-02T14:37:33",
};

const sampleUsageSnapshot = {
  community_id: "b6f92bbc-a4af-4240-8135-292d47563339",
  snapshot_date: "2025-06-11T23:59:59",
  subcounts: {
    access_statuses: [
      {
        download: {
          total_events: 60,
          total_volume: 61440.0,
          unique_files: 39,
          unique_parents: 39,
          unique_records: 39,
          unique_visitors: 60,
        },
        id: "open",
        label: "",
        view: {
          total_events: 60,
          unique_parents: 39,
          unique_records: 39,
          unique_visitors: 60,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "metadata-only",
        label: "",
        view: {
          total_events: 20,
          unique_parents: 13,
          unique_records: 13,
          unique_visitors: 20,
        },
      },
    ],
    file_types: [
      {
        download: {
          total_events: 60,
          total_volume: 61440.0,
          unique_files: 39,
          unique_parents: 39,
          unique_records: 39,
          unique_visitors: 60,
        },
        id: "pdf",
        label: "",
        view: {
          total_events: 60,
          unique_parents: 39,
          unique_records: 39,
          unique_visitors: 60,
        },
      },
    ],
    languages: [
      {
        download: {
          total_events: 40,
          total_volume: 40960.0,
          unique_files: 26,
          unique_parents: 26,
          unique_records: 26,
          unique_visitors: 40,
        },
        id: "eng",
        label: {"en": "English"},
        view: {
          total_events: 40,
          unique_parents: 26,
          unique_records: 26,
          unique_visitors: 40,
        },
      },
    ],
    resource_types: [
      {
        download: {
          total_events: 40,
          total_volume: 40960.0,
          unique_files: 26,
          unique_parents: 26,
          unique_records: 26,
          unique_visitors: 40,
        },
        id: "textDocument-journalArticle",
        label: {"en": "Journal Article"},
        view: {
          total_events: 40,
          unique_parents: 26,
          unique_records: 26,
          unique_visitors: 40,
        },
      },
      {
        download: {
          total_events: 20,
          total_volume: 20480.0,
          unique_files: 13,
          unique_parents: 13,
          unique_records: 13,
          unique_visitors: 20,
        },
        id: "textDocument-bookSection",
        label: {"en": "Book Section"},
        view: {
          total_events: 20,
          unique_parents: 13,
          unique_records: 13,
          unique_visitors: 20,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "textDocument-book",
        label: {"en": "Book"},
        view: {
          total_events: 20,
          unique_parents: 13,
          unique_records: 13,
          unique_visitors: 20,
        },
      },
    ],
    rights: {
      by_download: [
      {
        download: {
          total_events: 20,
          total_volume: 20480.0,
          unique_files: 13,
          unique_parents: 13,
          unique_records: 13,
          unique_visitors: 20,
        },
        id: "cc-by-sa-4.0",
        label: {"en": "Creative Commons Attribution-ShareAlike 4.0 International"},
        view: {
          total_events: 20,
          unique_parents: 13,
          unique_records: 13,
          unique_visitors: 20,
        },
      },
      ],
      by_view: [
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "cc-by-sa-4.0",
          label: {"en": "Creative Commons Attribution-ShareAlike 4.0 International"},
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
      ],
    },
    affiliations: {
      by_download: [
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "013v4ng57",
          label: "",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "03rmrcq20",
          label: "",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
      ],
      by_view: [
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "013v4ng57",
          label: "",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "03rmrcq20",
          label: "",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
      ],
    },
    countries: {
      by_download: [
        {
          download: {
            total_events: 60,
            total_volume: 61440.0,
            unique_files: 39,
            unique_parents: 39,
            unique_records: 39,
            unique_visitors: 60,
          },
          id: "US",
          label: "",
          view: {
            total_events: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
        },
      ],
      by_view: [
        {
          download: {
            total_events: 60,
            total_volume: 61440.0,
            unique_files: 39,
            unique_parents: 39,
            unique_records: 39,
            unique_visitors: 60,
          },
          id: "US",
          label: "",
          view: {
            total_events: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
        },
      ],
    },
    publishers: {
      by_download: [
        {
          download: {
            total_events: 40,
            total_volume: 40960.0,
            unique_files: 26,
            unique_parents: 26,
            unique_records: 26,
            unique_visitors: 40,
          },
          id: "Knowledge Commons",
          label: "",
          view: {
            total_events: 40,
            unique_parents: 26,
            unique_records: 26,
            unique_visitors: 40,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "Apocryphile Press",
          label: "",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "UBC",
          label: "",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
      ],
      by_view: [
        {
          download: {
            total_events: 40,
            total_volume: 40960.0,
            unique_files: 26,
            unique_parents: 26,
            unique_records: 26,
            unique_visitors: 40,
          },
          id: "Knowledge Commons",
          label: "",
          view: {
            total_events: 40,
            unique_parents: 26,
            unique_records: 26,
            unique_visitors: 40,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "Apocryphile Press",
          label: "",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "UBC",
          label: "",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
      ],
    },
    referrers: {
      by_download: [
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "https://works.hcommons.org/records/93d15-0z168/preview/test.pdf",
          label: "",
          view: {
            total_events: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "https://works.hcommons.org/records/k2vpp-4jr03/preview/test.pdf",
          label: "",
          view: {
            total_events: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "https://works.hcommons.org/records/trh07-zgc32/preview/test.pdf",
          label: "",
          view: {
            total_events: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
        },
      ],
      by_view: [
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "https://works.hcommons.org/records/93d15-0z168/preview/test.pdf",
          label: "",
          view: {
            total_events: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "https://works.hcommons.org/records/k2vpp-4jr03/preview/test.pdf",
          label: "",
          view: {
            total_events: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "https://works.hcommons.org/records/trh07-zgc32/preview/test.pdf",
          label: "",
          view: {
            total_events: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
        },
      ],
    },
    subjects: {
      by_download: [
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/2060143",
          label: "Mass incarceration",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/855500",
          label: "Children of prisoners--Services for",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/973589",
          label: "Inklings (Group of writers)",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/995415",
          label: "Legal assistance to prisoners--U.S. states",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/997916",
          label: "Library science",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/997974",
          label: "Library science--Standards",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/997987",
          label: "Library science literature",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "http://id.worldcat.org/fast/1424786",
          label: "Canadian literature--Bibliography",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "http://id.worldcat.org/fast/817954",
          label: "Arts, Canadian",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "http://id.worldcat.org/fast/821870",
          label: "Authors, Canadian",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
      ],
      by_view: [
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/2060143",
          label: "Mass incarceration",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/855500",
          label: "Children of prisoners--Services for",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/973589",
          label: "Inklings (Group of writers)",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/995415",
          label: "Legal assistance to prisoners--U.S. states",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/997916",
          label: "Library science",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/997974",
          label: "Library science--Standards",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 20,
            total_volume: 20480.0,
            unique_files: 13,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
          id: "http://id.worldcat.org/fast/997987",
          label: "Library science literature",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "http://id.worldcat.org/fast/1424786",
          label: "Canadian literature--Bibliography",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "http://id.worldcat.org/fast/817954",
          label: "Arts, Canadian",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
        {
          download: {
            total_events: 0,
            total_volume: 0.0,
            unique_files: 0,
            unique_parents: 0,
            unique_records: 0,
            unique_visitors: 0,
          },
          id: "http://id.worldcat.org/fast/821870",
          label: "Authors, Canadian",
          view: {
            total_events: 20,
            unique_parents: 13,
            unique_records: 13,
            unique_visitors: 20,
          },
        },
      ],
    },
    funders: {
      by_download: [
        {
          download: {
            total_events: 10,
            total_volume: 10240.0,
            unique_files: 7,
            unique_parents: 7,
            unique_records: 7,
            unique_visitors: 10,
          },
          id: "National Science Foundation",
          label: "",
          view: {
            total_events: 10,
            unique_parents: 7,
            unique_records: 7,
            unique_visitors: 10,
          },
        },
        {
          download: {
            total_events: 5,
            total_volume: 5120.0,
            unique_files: 3,
            unique_parents: 3,
            unique_records: 3,
            unique_visitors: 5,
          },
          id: "National Endowment for the Humanities",
          label: "",
          view: {
            total_events: 5,
            unique_parents: 3,
            unique_records: 3,
            unique_visitors: 5,
          },
        },
      ],
      by_view: [
        {
          download: {
            total_events: 10,
            total_volume: 10240.0,
            unique_files: 7,
            unique_parents: 7,
            unique_records: 7,
            unique_visitors: 10,
          },
          id: "National Science Foundation",
          label: "",
          view: {
            total_events: 10,
            unique_parents: 7,
            unique_records: 7,
            unique_visitors: 10,
          },
        },
        {
          download: {
            total_events: 5,
            total_volume: 5120.0,
            unique_files: 3,
            unique_parents: 3,
            unique_records: 3,
            unique_visitors: 5,
          },
          id: "National Endowment for the Humanities",
          label: "",
          view: {
            total_events: 5,
            unique_parents: 3,
            unique_records: 3,
            unique_visitors: 5,
          },
        },
      ],
    },
    periodicals: {
      by_download: [
        {
          download: {
            total_events: 15,
            total_volume: 15360.0,
            unique_files: 10,
            unique_parents: 10,
            unique_records: 10,
            unique_visitors: 15,
          },
          id: "Journal of Library Science",
          label: "",
          view: {
            total_events: 15,
            unique_parents: 10,
            unique_records: 10,
            unique_visitors: 15,
          },
        },
        {
          download: {
            total_events: 8,
            total_volume: 8192.0,
            unique_files: 5,
            unique_parents: 5,
            unique_records: 5,
            unique_visitors: 8,
          },
          id: "Digital Humanities Quarterly",
          label: "",
          view: {
            total_events: 8,
            unique_parents: 5,
            unique_records: 5,
            unique_visitors: 8,
          },
        },
      ],
      by_view: [
        {
          download: {
            total_events: 15,
            total_volume: 15360.0,
            unique_files: 10,
            unique_parents: 10,
            unique_records: 10,
            unique_visitors: 15,
          },
          id: "Journal of Library Science",
          label: "",
          view: {
            total_events: 15,
            unique_parents: 10,
            unique_records: 10,
            unique_visitors: 15,
          },
        },
        {
          download: {
            total_events: 8,
            total_volume: 8192.0,
            unique_files: 5,
            unique_parents: 5,
            unique_records: 5,
            unique_visitors: 8,
          },
          id: "Digital Humanities Quarterly",
          label: "",
          view: {
            total_events: 8,
            unique_parents: 5,
            unique_records: 5,
            unique_visitors: 8,
          },
        },
      ],
    },
    top_user_agents: {
      by_download: [
        {
          download: {
            total_events: 25,
            total_volume: 25600.0,
            unique_files: 17,
            unique_parents: 17,
            unique_records: 17,
            unique_visitors: 25,
          },
          id: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          label: "",
          view: {
            total_events: 25,
            unique_parents: 17,
            unique_records: 17,
            unique_visitors: 25,
          },
        },
        {
          download: {
            total_events: 12,
            total_volume: 12288.0,
            unique_files: 8,
            unique_parents: 8,
            unique_records: 8,
            unique_visitors: 12,
          },
          id: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
          label: "",
          view: {
            total_events: 12,
            unique_parents: 8,
            unique_records: 8,
            unique_visitors: 12,
          },
        },
      ],
      by_view: [
        {
          download: {
            total_events: 25,
            total_volume: 25600.0,
            unique_files: 17,
            unique_parents: 17,
            unique_records: 17,
            unique_visitors: 25,
          },
          id: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
          label: "",
          view: {
            total_events: 25,
            unique_parents: 17,
            unique_records: 17,
            unique_visitors: 25,
          },
        },
        {
          download: {
            total_events: 12,
            total_volume: 12288.0,
            unique_files: 8,
            unique_parents: 8,
            unique_records: 8,
            unique_visitors: 12,
          },
          id: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
          label: "",
          view: {
            total_events: 12,
            unique_parents: 8,
            unique_records: 8,
            unique_visitors: 12,
          },
        },
      ],
    },
  },
  timestamp: "2025-06-20T19:30:18",
  totals: {
    download: {
      total_events: 60,
      total_volume: 61440.0,
      unique_files: 39,
      unique_parents: 39,
      unique_records: 39,
      unique_visitors: 60,
    },
    view: {
      total_events: 80,
      unique_parents: 52,
      unique_records: 52,
      unique_visitors: 80,
    },
  },
};

const sampleUsageDelta = {
  community_id: "b6f92bbc-a4af-4240-8135-292d47563339",
  period_end: "2025-05-30T23:59:59",
  period_start: "2025-05-30T00:00:00",
  subcounts: {
    access_statuses: [
      {
        download: {
          total_events: 6,
          total_volume: 6144.0,
          unique_files: 3,
          unique_parents: 3,
          unique_records: 3,
          unique_visitors: 6,
        },
        id: "open",
        label: "",
        view: {
          total_events: 6,
          unique_parents: 3,
          unique_records: 3,
          unique_visitors: 6,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "metadata-only",
        label: "",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
    ],
    affiliations: [
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "013v4ng57",
        label: "",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "03rmrcq20",
        label: "",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
    ],
    countries: [
      {
        download: {
          total_events: 6,
          total_volume: 6144.0,
          unique_files: 3,
          unique_parents: 3,
          unique_records: 3,
          unique_visitors: 6,
        },
        id: "US",
        label: "",
        view: {
          total_events: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
      },
    ],
    file_types: [
      {
        download: {
          total_events: 6,
          total_volume: 6144.0,
          unique_files: 3,
          unique_parents: 3,
          unique_records: 3,
          unique_visitors: 6,
        },
        id: "pdf",
        label: "",
        view: {
          total_events: 6,
          unique_parents: 3,
          unique_records: 3,
          unique_visitors: 6,
        },
      },
    ],
    funders: [],
    languages: [
      {
        download: {
          total_events: 4,
          total_volume: 4096.0,
          unique_files: 2,
          unique_parents: 2,
          unique_records: 2,
          unique_visitors: 4,
        },
        id: "eng",
        label: {"en": "English"},
        view: {
          total_events: 4,
          unique_parents: 2,
          unique_records: 2,
          unique_visitors: 4,
        },
      },
    ],
    rights: [
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "cc-by-sa-4.0",
        label: {"en": "Creative Commons Attribution-ShareAlike 4.0 International"},
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
    ],
    periodicals: [],
    publishers: [
      {
        download: {
          total_events: 4,
          total_volume: 4096.0,
          unique_files: 2,
          unique_parents: 2,
          unique_records: 2,
          unique_visitors: 4,
        },
        id: "Knowledge Commons",
        label: "",
        view: {
          total_events: 4,
          unique_parents: 2,
          unique_records: 2,
          unique_visitors: 4,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "Apocryphile Press",
        label: "",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "UBC",
        label: "",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
    ],
    referrers: [
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "https://works.hcommons.org/records/93d15-0z168/preview/test.pdf",
        label: "",
        view: {
          total_events: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "https://works.hcommons.org/records/k2vpp-4jr03/preview/test.pdf",
        label: "",
        view: {
          total_events: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "https://works.hcommons.org/records/trh07-zgc32/preview/test.pdf",
        label: "",
        view: {
          total_events: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
      },
    ],
    resource_types: [
      {
        download: {
          total_events: 4,
          total_volume: 4096.0,
          unique_files: 2,
          unique_parents: 2,
          unique_records: 2,
          unique_visitors: 4,
        },
        id: "textDocument-journalArticle",
        label: {"en": "Journal Article"},
        view: {
          total_events: 4,
          unique_parents: 2,
          unique_records: 2,
          unique_visitors: 4,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "textDocument-bookSection",
        label: {"en": "Book Section"},
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "textDocument-book",
        label: {"en": "Book"},
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
    ],
    subjects: [
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "http://id.worldcat.org/fast/2060143",
        label: "Mass incarceration",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "http://id.worldcat.org/fast/855500",
        label: "Children of prisoners--Services for",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "http://id.worldcat.org/fast/973589",
        label: "Inklings (Group of writers)",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "http://id.worldcat.org/fast/995415",
        label: "Legal assistance to prisoners--U.S. states",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "http://id.worldcat.org/fast/997916",
        label: "Library science",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "http://id.worldcat.org/fast/997974",
        label: "Library science--Standards",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 2,
          total_volume: 2048.0,
          unique_files: 1,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
        id: "http://id.worldcat.org/fast/997987",
        label: "Library science literature",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/1424786",
        label: "Canadian literature--Bibliography",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/817954",
        label: "Arts, Canadian",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/821870",
        label: "Authors, Canadian",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/845111",
        label: "Canadian literature",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/845142",
        label: "Canadian literature--Periodicals",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/845170",
        label: "Canadian periodicals",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/845184",
        label: "Canadian prose literature",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/911328",
        label: "English language--Lexicography--History",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/911660",
        label: "English language--Spoken English--Research",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/911979",
        label: "English language--Written English--History",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
      {
        download: {
          total_events: 0,
          total_volume: 0.0,
          unique_files: 0,
          unique_parents: 0,
          unique_records: 0,
          unique_visitors: 0,
        },
        id: "http://id.worldcat.org/fast/934875",
        label: "French-Canadian literature",
        view: {
          total_events: 2,
          unique_parents: 1,
          unique_records: 1,
          unique_visitors: 2,
        },
      },
    ],
  },
  timestamp: "2025-06-20T19:30:10",
  totals: {
    download: {
      total_events: 6,
      total_volume: 6144.0,
      unique_files: 3,
      unique_parents: 3,
      unique_records: 3,
      unique_visitors: 6,
    },
    view: { total_events: 8, unique_parents: 4, unique_records: 4, unique_visitors: 8 },
  },
};

export {
  sampleRecordDelta,
  sampleUsageDelta,
  sampleRecordSnapshot,
  sampleUsageSnapshot,
};
