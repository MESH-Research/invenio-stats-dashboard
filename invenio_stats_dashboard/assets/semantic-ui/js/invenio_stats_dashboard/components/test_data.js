import { i18next } from "@translations/invenio_stats_dashboard/i18next";
import React from "react";

// Generate dates for multiple years
const generateDates = () => {
  const dates = [];
  const today = new Date();
  const startDate = new Date(today.getFullYear() - 3, 0, 1); // Start from 3 years ago
  const endDate = today;

  let currentDate = new Date(startDate);
  while (currentDate <= endDate) {
    dates.push(currentDate.toISOString().split('T')[0]);
    currentDate.setDate(currentDate.getDate() + 1);
  }
  return dates;
};

// Define resource types with IDs and labels
const RESOURCE_TYPES = {
  'dataset': {
    id: 'dataset',
    label: 'Dataset',
    ratio: 0.4
  },
  'software': {
    id: 'software',
    label: 'Software',
    ratio: 0.2
  },
  'research_paper': {
    id: 'research_paper',
    label: 'Research Paper',
    ratio: 0.3
  },
  'other': {
    id: 'other',
    label: 'Other',
    ratio: 0.1
  }
};

// Define subject headings with IDs and labels
const SUBJECT_HEADINGS = {
  'computer_science': {
    id: 'computer_science',
    label: 'Computer Science',
    ratio: 0.25
  },
  'environmental_science': {
    id: 'environmental_science',
    label: 'Environmental Science',
    ratio: 0.2
  },
  'biology': {
    id: 'biology',
    label: 'Biology',
    ratio: 0.15
  },
  'physics': {
    id: 'physics',
    label: 'Physics',
    ratio: 0.15
  },
  'social_sciences': {
    id: 'social_sciences',
    label: 'Social Sciences',
    ratio: 0.15
  },
  'other': {
    id: 'other',
    label: 'Other',
    ratio: 0.1
  }
};

// Generate random data points with sub-counts
const generateDataPoints = (baseValue, variance) => {
  return generateDates().map(date => {
    const totalValue = Math.floor(baseValue + (Math.random() * variance));
    const resourceTypeCounts = {};
    const subjectHeadingCounts = {};

    // Generate resource type sub-counts
    Object.values(RESOURCE_TYPES).forEach(({ id, label, ratio }) => {
      resourceTypeCounts[id] = {
        count: Math.floor(totalValue * ratio * (0.8 + Math.random() * 0.4)),
        label: label
      };
    });

    // Generate subject heading sub-counts
    Object.values(SUBJECT_HEADINGS).forEach(({ id, label, ratio }) => {
      subjectHeadingCounts[id] = {
        count: Math.floor(totalValue * ratio * (0.8 + Math.random() * 0.4)),
        label: label
      };
    });

    return {
      date,
      value: totalValue,
      resourceTypes: resourceTypeCounts,
      subjectHeadings: subjectHeadingCounts
    };
  });
};

// Generate cumulative data points with sub-counts
const generateCumulativeDataPoints = (baseValue, dailyBaseValue, dailyVariance) => {
  let cumulative = baseValue;
  let cumulativeResourceTypes = {};
  let cumulativeSubjectHeadings = {};

  // Initialize cumulative counts
  Object.values(RESOURCE_TYPES).forEach(({ id, label, ratio }) => {
    cumulativeResourceTypes[id] = {
      count: Math.floor(baseValue * ratio),
      label: label
    };
  });

  Object.values(SUBJECT_HEADINGS).forEach(({ id, label, ratio }) => {
    cumulativeSubjectHeadings[id] = {
      count: Math.floor(baseValue * ratio),
      label: label
    };
  });

  return generateDates().map(date => {
    const dailyValue = Math.floor(dailyBaseValue + (Math.random() * dailyVariance));
    cumulative += dailyValue;

    // Update cumulative resource type counts
    Object.values(RESOURCE_TYPES).forEach(({ id, label, ratio }) => {
      const dailyTypeValue = Math.floor(dailyValue * ratio * (0.8 + Math.random() * 0.4));
      cumulativeResourceTypes[id] = {
        count: cumulativeResourceTypes[id].count + dailyTypeValue,
        label: label
      };
    });

    // Update cumulative subject heading counts
    Object.values(SUBJECT_HEADINGS).forEach(({ id, label, ratio }) => {
      const dailySubjectValue = Math.floor(dailyValue * ratio * (0.8 + Math.random() * 0.4));
      cumulativeSubjectHeadings[id] = {
        count: cumulativeSubjectHeadings[id].count + dailySubjectValue,
        label: label
      };
    });

    return {
      date,
      value: cumulative,
      resourceTypes: { ...cumulativeResourceTypes },
      subjectHeadings: { ...cumulativeSubjectHeadings }
    };
  });
};

// Sample record data
const sampleRecords = [
  {
    id: "climate-change-analysis-2023",
    title: "Dataset: Climate Change Analysis 2023",
    views: 1234567,
    downloads: 234567
  },
  {
    id: "ai-ethics-research",
    title: "Research Paper: AI Ethics",
    views: 987654,
    downloads: 187654
  },
  {
    id: "global-population-trends",
    title: "Dataset: Global Population Trends",
    views: 876543,
    downloads: 176543
  },
  {
    id: "quantum-computing-paper",
    title: "Research Paper: Quantum Computing",
    views: 765432,
    downloads: 165432
  },
  {
    id: "renewable-energy-sources",
    title: "Dataset: Renewable Energy Sources",
    views: 654321,
    downloads: 154321
  },
  {
    id: "genomics-research-2024",
    title: "Dataset: Human Genome Analysis 2024",
    views: 543210,
    downloads: 143210
  },
  {
    id: "blockchain-technology",
    title: "Research Paper: Blockchain Applications",
    views: 432109,
    downloads: 132109
  },
  {
    id: "ocean-ecosystem-data",
    title: "Dataset: Pacific Ocean Ecosystem",
    views: 321098,
    downloads: 121098
  },
  {
    id: "machine-learning-algorithms",
    title: "Software: ML Algorithm Library",
    views: 210987,
    downloads: 110987
  },
  {
    id: "urban-planning-study",
    title: "Research Paper: Smart Cities",
    views: 198765,
    downloads: 98765
  },
  {
    id: "biodiversity-database",
    title: "Dataset: Amazon Rainforest Species",
    views: 187654,
    downloads: 87654
  },
  {
    id: "cybersecurity-framework",
    title: "Software: Security Framework",
    views: 176543,
    downloads: 76543
  },
  {
    id: "economic-forecast-2024",
    title: "Dataset: Global Economic Trends",
    views: 165432,
    downloads: 65432
  },
  {
    id: "medical-imaging-software",
    title: "Software: Medical Image Analysis",
    views: 154321,
    downloads: 54321
  },
  {
    id: "climate-models-2024",
    title: "Dataset: Climate Prediction Models",
    views: 143210,
    downloads: 43210
  },
  {
    id: "robotics-research",
    title: "Research Paper: Autonomous Systems",
    views: 132109,
    downloads: 32109
  },
  {
    id: "satellite-imagery",
    title: "Dataset: Earth Observation Data",
    views: 121098,
    downloads: 21098
  },
  {
    id: "data-visualization-tool",
    title: "Software: Interactive Visualizations",
    views: 110987,
    downloads: 10987
  },
  {
    id: "social-media-analysis",
    title: "Dataset: Social Network Patterns",
    views: 109876,
    downloads: 9876
  },
  {
    id: "quantum-algorithms",
    title: "Software: Quantum Computing Library",
    views: 98765,
    downloads: 8765
  }
];

// Test data for stats components
const testStatsData = {
  // Regular stats data (daily values)
  recordCount: generateDataPoints(25, 20),
  uploaders: generateDataPoints(12, 13),
  dataVolume: generateDataPoints(50000000, 100000000),
  views: generateDataPoints(100, 200),
  downloads: generateDataPoints(40, 50),
  traffic: generateDataPoints(2500000000, 5000000000),

  // Cumulative stats data (running totals)
  cumulativeRecordCount: generateCumulativeDataPoints(12500, 50, 40),
  cumulativeUploaders: generateCumulativeDataPoints(2500, 25, 20),
  cumulativeDataVolume: generateCumulativeDataPoints(2500000000000, 200000000, 300000000),
  cumulativeViews: generateCumulativeDataPoints(250000, 250, 300),
  cumulativeDownloads: generateCumulativeDataPoints(75000, 100, 120),
  cumulativeTraffic: generateCumulativeDataPoints(2500000000000, 5000000000, 7500000000),

  // License data
  licenses: [
    { name: "Creative Commons Attribution 4.0 International", id: "cc-by-4.0",  count: 450, percentage: 45 },
    { name: "Creative Commons Attribution-ShareAlike 4.0 International", id: "cc-by-sa-4.0", count: 250, percentage: 25 },
    { name: "Creative Commons Attribution-NonCommercial 4.0 International", id: "cc-by-nc-4.0", count: 150, percentage: 15 },
    { name: "Creative Commons Zero 1.0 Universal", id: "cc0-1.0", count: 50, percentage: 5 },
  ],
  // Affiliation data
  affiliations: [
    { name: "University of California, Berkeley", count: 175, percentage: 35 },
    { name: "Massachusetts Institute of Technology", count: 150, percentage: 30 },
    { name: "Stanford University", count: 100, percentage: 20 },
    { name: "Harvard University", count: 50, percentage: 10 },
    { name: "Other", count: 25, percentage: 5 },
  ],
  // Funder data
  funders: [
    { name: "National Science Foundation", count: 300, percentage: 30 },
    { name: "National Institutes of Health", count: 250, percentage: 25 },
    { name: "European Research Council", count: 200, percentage: 20 },
    { name: "Wellcome Trust", count: 150, percentage: 15 },
    { name: "Other", count: 100, percentage: 10 },
  ],
  // Settings
  use_binary_filesize: true,

  // Countries data
  topCountries: [
    { name: "United States", count: 25432, percentage: 25.4 },
    { name: "United Kingdom", count: 15321, percentage: 15.3 },
    { name: "Germany", count: 12210, percentage: 12.2 },
    { name: "France", count: 8109, percentage: 8.1 },
    { name: "Canada", count: 6543, percentage: 6.5 },
    { name: "Australia", count: 5432, percentage: 5.4 },
    { name: "Japan", count: 4321, percentage: 4.3 },
    { name: "China", count: 3210, percentage: 3.2 },
    { name: "India", count: 2109, percentage: 2.1 },
    { name: "Brazil", count: 1098, percentage: 1.1 },
    { name: "Italy", count: 987, percentage: 1.0 },
    { name: "Spain", count: 876, percentage: 0.9 },
    { name: "Netherlands", count: 765, percentage: 0.8 },
    { name: "South Korea", count: 654, percentage: 0.7 },
    { name: "Sweden", count: 543, percentage: 0.5 },
    { name: "Switzerland", count: 432, percentage: 0.4 },
    { name: "Belgium", count: 321, percentage: 0.3 },
    { name: "Austria", count: 210, percentage: 0.2 },
    { name: "Denmark", count: 109, percentage: 0.1 },
    { name: "Norway", count: 98, percentage: 0.1 },
    { name: "Finland", count: 87, percentage: 0.1 },
    { name: "Portugal", count: 76, percentage: 0.1 },
    { name: "Ireland", count: 65, percentage: 0.1 },
    { name: "Greece", count: 54, percentage: 0.1 },
    { name: "Poland", count: 43, percentage: 0.0 },
    { name: "Czech Republic", count: 32, percentage: 0.0 },
    { name: "Hungary", count: 21, percentage: 0.0 },
    { name: "Romania", count: 10, percentage: 0.0 },
    { name: "Bulgaria", count: 9, percentage: 0.0 },
    { name: "Croatia", count: 8, percentage: 0.0 }
  ],
  accessRights: [
    { name: "Open Access", count: 25432, percentage: 25.4 },
    { name: "Embargoed", count: 15321, percentage: 15.3 },
    { name: "Restricted", count: 12210, percentage: 12.2 },
    { name: "Metadata Only", count: 8109, percentage: 8.1 }
  ],

  // Resource types data with IDs and labels
  resourceTypes: [
    { id: 'dataset', name: 'Dataset', count: 25000, percentage: 25.0 },
    { id: 'research_paper', name: 'Research Paper', count: 20000, percentage: 20.0 },
    { id: 'software', name: 'Software', count: 15000, percentage: 15.0 },
    { id: 'other', name: 'Other', count: 10000, percentage: 10.0 }
  ],

  // Referrer domains data
  referrerDomains: [
    { name: "google.com", count: 3000, percentage: 30 },
    { name: "scholar.google.com", count: 2000, percentage: 20 },
    { name: "github.com", count: 1500, percentage: 15 },
    { name: "linkedin.com", count: 1000, percentage: 10 },
    { name: "Other", count: 2500, percentage: 25 },
  ],

  // Most downloaded records data
  mostDownloadedRecords: sampleRecords.map(record => ({
    title: record.title,
    downloads: record.downloads,
    percentage: Math.round((record.downloads / 918517) * 100), // Total of all downloads
    id: record.id,
  })),

  // Most viewed records data
  mostViewedRecords: sampleRecords.map(record => ({
    title: record.title,
    views: record.views,
    percentage: Math.round((record.views / 4518517) * 100), // Total of all views
    id: record.id,
  })),
};

export { testStatsData, generateDataPoints, generateCumulativeDataPoints, sampleRecords, RESOURCE_TYPES, SUBJECT_HEADINGS };