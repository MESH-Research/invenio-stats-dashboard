// Mock i18next module used in numbers.js
jest.mock('@translations/i18next', () => ({
  i18next: {
    language: 'en',
    t: (key, args) => {
      if (key.startsWith('filesize.units.')) {
        return key.split('.').pop();
      }
      if (key === 'numberFormat.default') {
        // Mimic toLocaleString({ maximumFractionDigits: 0 })
        return Math.round(args.number).toString();
      }
      if (key.startsWith('numberFormat.')) {
        return args && typeof args.number !== 'undefined' ? args.number.toString() : '';
      }
      return key;
    },
  },
}));

import { formatNumber } from './numbers';

// Patch toLocaleString for predictable output in tests
const originalToLocaleString = Number.prototype.toLocaleString;
beforeAll(() => {
  Number.prototype.toLocaleString = function (locale, opts) {
    if (opts && typeof opts.maximumFractionDigits === 'number') {
      return this.toFixed(opts.maximumFractionDigits);
    }
    return this.toString();
  };
});
afterAll(() => {
  Number.prototype.toLocaleString = originalToLocaleString;
});

describe('formatNumber', () => {
  it('formats default numbers with no decimals', () => {
    expect(formatNumber(1234)).toBe('1234');
    expect(formatNumber(1234.56)).toBe('1235');
  });

  it('formats compact numbers above threshold', () => {
    expect(formatNumber(12345678, 'compact')).toMatch(/\d+(\.\d+)?/);
  });

  it('formats percent', () => {
    expect(formatNumber(0.123, 'percent')).toBe('0.123');
  });

  it('formats currency', () => {
    expect(formatNumber(1234.56, 'currency')).toBe('1234.56');
  });

  describe('filesize', () => {
    it('formats bytes < 1k', () => {
      expect(formatNumber(512, 'filesize')).toBe('512 Bytes');
    });
    it('formats 1 byte', () => {
      expect(formatNumber(1, 'filesize')).toBe('Bytes');
    });
    it('formats kB and MB (decimal)', () => {
      expect(formatNumber(1500, 'filesize')).toBe('1.5 kB');
      expect(formatNumber(1500000, 'filesize')).toBe('1.5 MB');
    });
    it('formats KiB and MiB (binary)', () => {
      expect(formatNumber(2048, 'filesize', { binary: true })).toBe('2.0 KiB');
      expect(formatNumber(1048576, 'filesize', { binary: true })).toBe('1.0 MiB');
    });
  });
});