// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import pako from 'pako';

/**
 * Serialize stats data to JSON format matching the API response structure
 *
 * @param {Array} stats - Array of yearly stats objects from the dashboard context
 * @param {string} communityId - Community ID or 'global'
 * @param {string} dateBasis - Date basis ("added", "created", "published")
 * @returns {Object} Serialized stats data in API response format
 */
export const serializeStatsToJson = (stats, communityId, dateBasis) => {
  // Initialize the response structure to match API format
  const response = {
    "usage-snapshot-category": {},
    "usage-delta-category": {},
    "record-snapshot-category": {},
    "record-delta-category": {}
  };

  // Process each yearly stats block
  stats.forEach(yearBlock => {
    if (!yearBlock || !yearBlock.data) {
      return;
    }

    const yearData = yearBlock.data;

    // Merge each category
    Object.keys(response).forEach(category => {
      if (yearData[category]) {
        mergeCategoryData(response[category], yearData[category]);
      }
    });
  });

  return response;
};

/**
 * Merge data from a yearly block into the response structure
 * @param {Object} target - The target category object to merge into
 * @param {Object} source - The source category object from a yearly block
 */
const mergeCategoryData = (target, source) => {
  Object.keys(source).forEach(subcategory => {
    if (!target[subcategory]) {
      target[subcategory] = {};
    }

    Object.keys(source[subcategory]).forEach(metric => {
      if (!target[subcategory][metric]) {
        target[subcategory][metric] = [];
      }

      // Merge data series objects by ID
      source[subcategory][metric].forEach(dataSeries => {
        const existingSeries = target[subcategory][metric].find(
          series => series.id === dataSeries.id
        );

        if (existingSeries) {
          // Merge the data arrays
          existingSeries.data = [...existingSeries.data, ...dataSeries.data];
        } else {
          // Add new data series
          target[subcategory][metric].push({
            ...dataSeries,
            data: [...dataSeries.data]
          });
        }
      });
    });
  });
};

/**
 * Create a tar.gz archive containing the JSON file
 *
 * @param {Array} stats - Array of yearly stats objects from the dashboard context
 * @param {string} communityId - Community ID or 'global'
 * @param {string} dateBasis - Date basis ("added", "created", "published")
 * @param {string} jsonFilename - Name for the JSON file inside the archive
 * @returns {Blob} Tar.gz archive blob ready for download
 */
export const createTarGzJsonBlob = (stats, communityId, dateBasis, jsonFilename) => {
  // Serialize the stats data to JSON format
  const jsonData = serializeStatsToJson(stats, communityId, dateBasis);

  // Convert to JSON string
  const jsonString = JSON.stringify(jsonData, null, 2);

  // Create a simple tar archive containing the JSON file
  const tarData = createTarArchive(jsonFilename, jsonString);

  // Compress the tar with gzip
  const compressedData = pako.gzip(tarData);

  // Create blob with appropriate MIME type
  return new Blob([compressedData], {
    type: 'application/gzip'
  });
};

/**
 * Create a simple tar archive containing a single file
 * This is a minimal tar implementation for our specific use case
 *
 * @param {string} filename - Name of the file to include in the archive
 * @param {string} content - Content of the file
 * @returns {Uint8Array} Tar archive data
 */
const createTarArchive = (filename, content) => {
  const encoder = new TextEncoder();
  const contentBytes = encoder.encode(content);
  const filenameBytes = encoder.encode(filename);

  // Tar header is 512 bytes
  const header = new Uint8Array(512);

  // Fill header with zeros first
  header.fill(0);

  // Set filename (100 bytes max)
  header.set(filenameBytes.slice(0, 100), 0);

  // Set file mode (8 bytes) - 0644
  const modeBytes = encoder.encode('0000644');
  header.set(modeBytes, 100);

  // Set owner UID (8 bytes)
  const uidBytes = encoder.encode('0000000');
  header.set(uidBytes, 108);

  // Set owner GID (8 bytes)
  const gidBytes = encoder.encode('0000000');
  header.set(gidBytes, 116);

  // Set file size (12 bytes, octal)
  const sizeOctal = contentBytes.length.toString(8).padStart(11, '0') + ' ';
  const sizeBytes = encoder.encode(sizeOctal);
  header.set(sizeBytes, 124);

  // Set modification time (12 bytes, octal)
  const mtimeOctal = Math.floor(Date.now() / 1000).toString(8).padStart(11, '0') + ' ';
  const mtimeBytes = encoder.encode(mtimeOctal);
  header.set(mtimeBytes, 136);

  // Set type flag (1 byte) - '0' for regular file
  header[156] = 48; // '0'

  // Calculate checksum
  let checksum = 0;
  for (let i = 0; i < 512; i++) {
    if (i >= 148 && i < 156) {
      // Skip checksum field itself
      checksum += 32; // space character
    } else {
      checksum += header[i];
    }
  }

  // Set checksum (8 bytes, octal)
  const checksumOctal = checksum.toString(8).padStart(6, '0') + ' ';
  const checksumBytes = encoder.encode(checksumOctal);
  header.set(checksumBytes, 148);

  // Pad content to 512-byte boundary
  const paddingSize = (512 - (contentBytes.length % 512)) % 512;
  const paddedContent = new Uint8Array(contentBytes.length + paddingSize);
  paddedContent.set(contentBytes);

  // Combine header and content
  const tarData = new Uint8Array(header.length + paddedContent.length);
  tarData.set(header);
  tarData.set(paddedContent, header.length);

  return tarData;
};

/**
 * Package stats data as compressed tar.gz archive containing JSON file
 *
 * @param {Array} stats - Array of yearly stats objects from the dashboard context
 * @param {string} communityId - Community ID or 'global'
 * @param {string} dashboardType - Dashboard type (global or community)
 * @param {string} dateBasis - Date basis ("added", "created", "published")
 * @param {string} startDate - Start date in YYYY-MM-DD format (for filename)
 * @param {string} endDate - End date in YYYY-MM-DD format (for filename)
 * @param {string} filename - Optional custom filename
 */
export const packageStatsAsCompressedJson = (stats, communityId, dashboardType, dateBasis, startDate, endDate, filename = null) => {
  try {
    // Generate JSON filename
    const communityPrefix = dashboardType === 'global' ? 'global' : communityId;
    const datePrefix = startDate && endDate ? `_${startDate}_to_${endDate}` : '';
    const jsonFilename = `stats_series_${communityPrefix}${datePrefix}.json`;

    // Create tar.gz archive blob
    const blob = createTarGzJsonBlob(stats, communityId, dateBasis, jsonFilename);

    // Generate archive filename if not provided
    if (!filename) {
      filename = `stats_series_${communityPrefix}${datePrefix}.tar.gz`;
    }

    // Create download link and trigger download
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    console.log(`Downloaded stats as tar.gz archive: ${filename}`);
  } catch (error) {
    console.error('Error downloading stats as tar.gz archive:', error);
    throw error;
  }
};
