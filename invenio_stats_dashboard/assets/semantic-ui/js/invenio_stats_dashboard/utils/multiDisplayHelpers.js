import { formatNumber } from "./numbers";
import { CHART_COLORS } from '../constants';

/**
 * Transform multi-display data into chart-ready format
 *
 * @param {Array} rawData - Array of data items from the API (access rights, affiliations, etc.)
 * @param {number} pageSize - Number of top items to show individually
 * @param {string} searchField - Field name for search links (e.g., 'metadata.access_right.id', 'metadata.affiliations.affiliation')
 * @param {Array} colorPalette - Array of color arrays for chart styling
 * @returns {Object} Object containing transformedData, otherData, and totalCount
 */
const transformMultiDisplayData = (rawData, pageSize = 10, searchField, colorPalette = CHART_COLORS.secondary) => {
  if (!rawData || !Array.isArray(rawData)) {
    return {
      transformedData: [],
      otherData: null,
      totalCount: 0
    };
  }

  const totalCount = rawData.reduce((sum, item) => sum + item?.data?.[0]?.value?.[1] || 0, 0);

  const topXItems = rawData.slice(0, pageSize);
  const otherItems = rawData.slice(pageSize);

  const transformedData = topXItems.map((item, index) => {
    const value = item?.data?.[0]?.value?.[1] || 0;
    const percentage = totalCount > 0 ? Math.round((value / totalCount) * 100) : 0;
    return {
      name: item.name,
      value: value,
      percentage: percentage,
      id: item.id,
      link: searchField ? `/search?q=${searchField}:${item.id}` : null,
      itemStyle: {
        color: colorPalette[index % colorPalette.length][1]
      }
    };
  });

  const otherData = otherItems.length > 0 ? otherItems.reduce((acc, item) => {
    acc.value += item?.data?.[0]?.value?.[1] || 0;
    return acc;
  }, {
    id: "other",
    name: "Other",
    value: 0,
    itemStyle: {
      color: colorPalette[colorPalette.length - 1][1]
    }
  }) : null;

  if (otherData) {
    otherData.percentage = totalCount > 0 ? Math.round((otherData.value / totalCount) * 100) : 0;
  }

  return {
    transformedData,
    otherData,
    totalCount
  };
};

/**
 * Assemble rows for the table display from transformed data
 *
 * @param {Array} transformedData - Array of transformed data
 * @param {Object} otherData - Other data object (can be null)
 * @returns {Array} Array of row arrays for the table
 */
const assembleMultiDisplayRows = (transformedData, otherData) => {
  const allData = [
    ...transformedData,
    ...(otherData ? [otherData] : [])
  ];

  return allData.map(({ name, value, percentage, link }) => [
    null,
    link ? <a href={link} target="_blank" rel="noopener noreferrer">{name}</a> : name,
    `${formatNumber(value, 'compact')} (${percentage}%)`,
  ]);
};

// Exports
export { transformMultiDisplayData, assembleMultiDisplayRows };