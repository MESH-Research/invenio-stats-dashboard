// Part of the Invenio-Stats-Dashboard extension for InvenioRDM
// Copyright (C) 2025 Mesh Research
//
// Invenio-Stats-Dashboard is free software; you can redistribute it and/or modify
// it under the terms of the MIT License; see LICENSE file for more details.

import { i18next } from "@translations/invenio_stats_dashboard/i18next";

/**
 * Extract a localized label from a label object or return a string as-is.
 *
 * @param {string|Object} label - The label to extract. Can be a string or an object with language keys.
 * @param {string} targetLanguage - The target language code (e.g., 'en', 'fr', 'es').
 * @returns {string} The localized label string.
 */
export const extractLocalizedLabel = (label, targetLanguage) => {
  if (typeof label === 'string') {
    return label;
  }

  if (label && typeof label === 'object') {
    // First, try to get the target language directly
    if (label[targetLanguage]) {
      return label[targetLanguage];
    }

    // If target language not available, try English as fallback
    if (label.en) {
      // Use i18next to translate the English string to the target language
      return i18next.t(label.en, { lng: targetLanguage });
    }

    // If no English fallback, use the first available language
    const availableLanguages = Object.keys(label);
    if (availableLanguages.length > 0) {
      const firstLanguage = availableLanguages[0];
      const firstLabel = label[firstLanguage];
      // Translate the first available label to the target language
      return i18next.t(firstLabel, { lng: targetLanguage });
    }
  }

  return '';
};
