// Mock i18next module used in numbers.js
jest.mock('@translations/i18next', () => ({
  i18next: {
    language: 'en',
    t: (key, args) => {
      if (key.startsWith('filesize.units.')) {
        return key.split('.').pop();
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
  describe('default format', () => {
    it('formats whole numbers with no decimals', () => {
      expect(formatNumber(1234)).toBe('1,234');
      expect(formatNumber(0)).toBe('0');
      expect(formatNumber(-1234)).toBe('-1,234');
    });

    it('rounds decimal numbers to whole numbers', () => {
      expect(formatNumber(1234.56)).toBe('1,235');
      expect(formatNumber(1234.4)).toBe('1,234');
      expect(formatNumber(-1234.56)).toBe('-1,235');
    });
  });

  describe('compact format', () => {
    it('formats numbers above threshold in compact notation', () => {
      expect(formatNumber(12345678, 'compact')).toMatch(/\d+(\.\d+)?/);
      expect(formatNumber(1000000, 'compact')).toMatch(/\d+(\.\d+)?/);
    });

    it('uses default format for numbers below threshold', () => {
      expect(formatNumber(9999999, 'compact')).toBe('10M');
    });

    it('allows custom threshold', () => {
      expect(formatNumber(1000, 'compact', { compactThreshold: 100 })).toMatch(/\d+(\.\d+)?/);
    });
  });

  describe('percent format', () => {
    it('formats numbers as percentages', () => {
      expect(formatNumber(0.123, 'percent')).toBe('12.3%');
      expect(formatNumber(1.234, 'percent')).toBe('123.4%');
      expect(formatNumber(0.001, 'percent')).toBe('0.1%');
    });

    it('handles negative percentages', () => {
      expect(formatNumber(-0.123, 'percent')).toBe('-12.3%');
    });
  });

  describe('currency format', () => {
    it('formats numbers as USD currency', () => {
      expect(formatNumber(1234.56, 'currency')).toBe('$1,234.56');
      expect(formatNumber(0.99, 'currency')).toBe('$0.99');
    });

    it('handles negative currency values', () => {
      expect(formatNumber(-1234.56, 'currency')).toBe('-$1,234.56');
    });
  });

  describe('filesize format', () => {
    it('formats bytes < 1k', () => {
      expect(formatNumber(512, 'filesize')).toBe('512 Bytes');
      expect(formatNumber(0, 'filesize')).toBe('0 Bytes');
    });

    it('formats 1 byte', () => {
      expect(formatNumber(1, 'filesize')).toBe('Bytes');
    });

    it('formats decimal units (kB, MB, GB)', () => {
      expect(formatNumber(1500, 'filesize')).toBe('1.5 kB');
      expect(formatNumber(1500000, 'filesize')).toBe('1.5 MB');
      expect(formatNumber(1500000000, 'filesize')).toBe('1.5 GB');
    });

    it('formats binary units (KiB, MiB, GiB)', () => {
      expect(formatNumber(2048, 'filesize', { binary: true })).toBe('2.0 KiB');
      expect(formatNumber(1048576, 'filesize', { binary: true })).toBe('1.0 MiB');
      expect(formatNumber(1073741824, 'filesize', { binary: true })).toBe('1.0 GiB');
    });

    it('handles large filesizes', () => {
      expect(formatNumber(1e12, 'filesize')).toBe('1.0 TB');
      expect(formatNumber(1e15, 'filesize')).toBe('1.0 PB');
      expect(formatNumber(1e18, 'filesize')).toBe('1.0 EB');
    });

    it('handles binary large filesizes', () => {
      expect(formatNumber(Math.pow(1024, 4), 'filesize', { binary: true })).toBe('1.0 TiB');
      expect(formatNumber(Math.pow(1024, 5), 'filesize', { binary: true })).toBe('1.0 PiB');
      expect(formatNumber(Math.pow(1024, 6), 'filesize', { binary: true })).toBe('1.0 EiB');
    });
  });

  describe('error handling', () => {
    it('handles invalid input gracefully', () => {
      expect(formatNumber(NaN)).toBe('NaN');
      expect(formatNumber(Infinity)).toBe('∞');
      expect(formatNumber(-Infinity)).toBe('-∞');
    });

    it('handles invalid format gracefully', () => {
      expect(formatNumber(1234, 'invalid')).toBe('1,234');
    });
  });
});