import { catInputToIso, catDateTimeInput, catDateKey, formatCatDateTime, utcClockToCat, catClockToUtc } from './clinicalTime';
import { formatSessionDateTime } from '../admin/AdminConstants';

test('CAT input preserves the instant across day and year boundaries', () => {
  expect(catInputToIso('2026-10-06T14:00')).toBe('2026-10-06T12:00:00.000Z');
  expect(catInputToIso('2027-01-01T00:30')).toBe('2026-12-31T22:30:00.000Z');
  expect(catDateTimeInput('2026-12-31T22:30:00Z')).toBe('2027-01-01T00:30');
  expect(catDateKey('2026-12-31T22:30:00Z')).toBe('2027-01-01');
  expect(() => catInputToIso('')).toThrow();
});

test('booking displays use CAT for both UTC and local-offset records', () => {
  const utc = formatSessionDateTime('2026-10-06T12:00:00Z');
  expect(utc.time).toBe('14:00');
  expect(formatSessionDateTime('2026-10-06T14:00:00+02:00')).toEqual(utc);
  expect(formatSessionDateTime('2026-10-06T12:00:00')).toEqual(utc);
  expect(formatCatDateTime('2026-10-06T12:00:00Z')).toContain('14:00 CAT');
});

test('editing CAT working hours preserves the stored UTC clock', () => {
  expect(utcClockToCat('08:00')).toBe('10:00');
  expect(catClockToUtc(utcClockToCat('08:00'))).toBe('08:00');
  expect(catClockToUtc('08:00')).toBe('06:00');
});
