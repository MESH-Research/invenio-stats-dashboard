import { i18next } from "@translations/invenio_stats_dashboard/i18next";

/**
 * Formats numbers for display, including compact, default, percent, currency, and filesize formats.
 *
 * @param {number} number - The number to format.
 * @param {string} format - The format type ('default', 'compact', 'percent', 'currency', 'filesize').
 * @param {object} options - Additional options (compactThreshold, binary, etc).
 * @returns {string} - The formatted number string.
 */
export function formatNumber(number, format = 'default', options = {}) {
  // Filesize formatting
  if (format === 'filesize') {
    const binary = options.binary || false;
    const base = binary ? 1024 : 1000;
    const prefixes = binary
      ? ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
      : ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    if (number === 1) {
      return 'Bytes';
    } else if (number < base) {
      // Localize the number and the unit
      const localizedNumber = number.toLocaleString(i18next.language, { maximumFractionDigits: 0 });
      return `${localizedNumber} Bytes`;
    } else {
      let i = -1;
      let value = number;
      do {
        value = value / base;
        i++;
      } while (value >= base && i < prefixes.length - 1);
      const localizedNumber = value.toLocaleString(i18next.language, { maximumFractionDigits: 1 });
      return `${localizedNumber} ${prefixes[i]}`;
    }
  }

  const { compactThreshold = 10_000_000 } = options;

  // Create number formatter based on format type
  const formatter = new Intl.NumberFormat(i18next.language, {
    // Default format
    default: {
      maximumFractionDigits: 0,
      minimumFractionDigits: 0
    },
    // Compact format for large numbers
    compact: {
      notation: 'compact',
      maximumFractionDigits: 2,
      minimumFractionDigits: 0
    },
    // Percentage format
    percent: {
      style: 'percent',
      maximumFractionDigits: 1
    },
    // Currency format
    currency: {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 2
    }
  }[format]);

  return formatter.format(number);
}
