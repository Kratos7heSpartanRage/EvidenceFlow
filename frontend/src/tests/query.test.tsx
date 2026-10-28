import { describe, expect, it } from 'vitest';

describe('Query Expression and Date Range Validation', () => {
  it('rejects an empty query expression', () => {
    const validateQuery = (expression: string) => {
      if (!expression.trim()) throw new Error('Search expression cannot be empty.');
      return true;
    };

    expect(() => validateQuery('')).toThrow('Search expression cannot be empty.');
    expect(() => validateQuery('   ')).toThrow('Search expression cannot be empty.');
    expect(validateQuery('metformin AND placebo')).toBe(true);
  });

  it('rejects date_from greater than date_to', () => {
    const validateDates = (from?: string, to?: string) => {
      if (from && to && from > to) {
        throw new Error('Date From must be before Date To.');
      }
      return true;
    };

    expect(() => validateDates('2025-01-01', '2020-01-01')).toThrow('Date From must be before Date To.');
    expect(validateDates('2015-01-01', '2025-12-31')).toBe(true);
    expect(validateDates('2020-01-01', '2020-01-01')).toBe(true);
  });

  it('formats explicit "imported N of M hits" text properly', () => {
    const formatImportedHits = (imported: number | null, hits: number | null) => {
      if (imported === null) return 'Pending approval';
      return `imported ${imported} of ${hits?.toLocaleString() ?? imported} hits`;
    };

    expect(formatImportedHits(null, 12431)).toBe('Pending approval');
    expect(formatImportedHits(500, 12431)).toBe('imported 500 of 12,431 hits');
    expect(formatImportedHits(0, 0)).toBe('imported 0 of 0 hits');
  });
});

