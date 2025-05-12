import { i18next } from "@translations/i18next";

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
      return i18next.t('filesize.units.Bytes');
    } else if (number < base) {
      // Localize the number and the unit
      const localizedNumber = number.toLocaleString(i18next.language, { maximumFractionDigits: 0 });
      return `${localizedNumber} ${i18next.t('filesize.units.Bytes')}`;
    } else {
      let i = -1;
      let value = number;
      do {
        value = value / base;
        i++;
      } while (value >= base && i < prefixes.length - 1);
      const localizedNumber = value.toLocaleString(i18next.language, { maximumFractionDigits: 1 });
      const localizedUnit = i18next.t(`filesize.units.${prefixes[i]}`);
      return `${localizedNumber} ${localizedUnit}`;
    }
  }

  const { compactThreshold = 10_000_000 } = options;
  // If number is above threshold and format is 'compact', use compact notation
  if (number >= compactThreshold && format === 'compact') {
    return i18next.t(`numberFormat.${format}`, {
      number: number,
      formatParams: {
        number: {
          notation: 'compact',
          maximumFractionDigits: 2,
          minimumFractionDigits: 0
        }
      }
    });
  }

  // Otherwise use the specified format
  return i18next.t(`numberFormat.${format}`, {
    number: number,
    formatParams: {
      number: {
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
      }[format]
    }
  });
}
