import React from "react";

// Generate dates for the last 12 months
const generateDates = () => {
  const dates = [];
  const today = new Date();
  for (let i = 11; i >= 0; i--) {
    const date = new Date(today.getFullYear(), today.getMonth() - i, 1);
    dates.push(date.toISOString().split('T')[0]);
  }
  return dates;
};

// Generate random data points
const generateDataPoints = (baseValue, variance) => {
  return generateDates().map(date => ({
    date,
    value: Math.floor(baseValue + (Math.random() * variance))
  }));
};

// Sample record data
const sampleRecords = [
  {
    id: "climate-change-analysis-2023",
    title: "Dataset: Climate Change Analysis 2023",
    views: "1,234,567",
    downloads: "234,567"
  },
  {
    id: "ai-ethics-research",
    title: "Research Paper: AI Ethics",
    views: "987,654",
    downloads: "187,654"
  },
  {
    id: "global-population-trends",
    title: "Dataset: Global Population Trends",
    views: "876,543",
    downloads: "176,543"
  },
  {
    id: "quantum-computing-paper",
    title: "Research Paper: Quantum Computing",
    views: "765,432",
    downloads: "165,432"
  },
  {
    id: "renewable-energy-sources",
    title: "Dataset: Renewable Energy Sources",
    views: "654,321",
    downloads: "154,321"
  }
];

// Sample country data for the map
const sampleCountries = [
  { name: "United States", value: 1000 },
  { name: "United Kingdom", value: 800 },
  { name: "Germany", value: 600 },
  { name: "France", value: 500 },
  { name: "Japan", value: 400 },
  { name: "Canada", value: 300 },
  { name: "Australia", value: 250 },
  { name: "Brazil", value: 200 },
  { name: "India", value: 150 },
  { name: "China", value: 100 }
];

const testStats = {
  views: generateDataPoints(1000, 500),
  downloads: generateDataPoints(500, 300),
  dataVolume: generateDataPoints(2000, 1000),
  traffic: generateDataPoints(1500, 800),
  uploaders: generateDataPoints(50, 30),
  recordCount: generateDataPoints(200, 100),
  topCountries: sampleCountries
};

const testRecordData = {
  mostViewed: sampleRecords.map(record => [
    "file outline",
    <a href={`/records/${record.id}`}>{record.title}</a>,
    record.views
  ]),
  mostDownloaded: sampleRecords.map(record => [
    "file outline",
    <a href={`/records/${record.id}`}>{record.title}</a>,
    record.downloads
  ])
};

export { testStats, testRecordData };