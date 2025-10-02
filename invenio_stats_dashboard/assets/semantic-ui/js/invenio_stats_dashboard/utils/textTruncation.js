// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import React from 'react';
import { Popup } from 'semantic-ui-react';

/**
 * Truncates text to fit within approximately two lines of display
 * @param {string} text - The text to truncate
 * @param {number} maxLength - Maximum character length (default: 60)
 * @returns {string} Truncated text with ellipsis if needed
 */
export const truncateForTwoLines = (text, maxLength = 60) => {
  if (!text || typeof text !== 'string') {
    return text || '';
  }

  if (text.length <= maxLength) {
    return text;
  }

  // Find the last space before the max length to avoid cutting words
  const truncated = text.substring(0, maxLength);
  const lastSpaceIndex = truncated.lastIndexOf(' ');

  if (lastSpaceIndex > maxLength * 0.7) {
    // If we found a space in the last 30% of the text, use it
    return text.substring(0, lastSpaceIndex) + '...';
  } else {
    // Otherwise, just cut at max length
    return truncated + '...';
  }
};

/**
 * Creates a truncated title component with tooltip for full text
 * @param {string} title - The full title text
 * @param {string|React.ReactElement} linkElement - Optional link element to wrap the title
 * @param {number} maxLength - Maximum character length (default: 60)
 * @returns {React.ReactElement} Truncated title with tooltip
 */
export const createTruncatedTitle = (title, linkElement = null, maxLength = 60) => {
  const truncatedTitle = truncateForTwoLines(title, maxLength);

  if (truncatedTitle === title) {
    return linkElement || title;
  }

  const truncatedElement = linkElement ?
    React.cloneElement(linkElement, { children: truncatedTitle }) :
    truncatedTitle;

  return (
    <Popup
      content={title}
      position="top center"
      size="mini"
      trigger={truncatedElement}
      className="tooltip"
    />
  );
};
