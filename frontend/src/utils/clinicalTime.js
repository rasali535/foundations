export const CLINICAL_TIME_ZONE = 'Africa/Gaborone';

// Legacy timestamps without an offset are stored as UTC, never browser-local time.
export const clinicalDate = (value) => {
  if (value instanceof Date) return value;
  const raw = String(value || '');
  return new Date(/^\d{4}-\d{2}-\d{2}T/.test(raw) && !/(Z|[+-]\d{2}:?\d{2})$/i.test(raw) ? `${raw}Z` : raw);
};

export const catDateTimeInput = (value = new Date()) => {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: CLINICAL_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(clinicalDate(value));
  const part = (type) => parts.find(item => item.type === type).value;
  return `${part('year')}-${part('month')}-${part('day')}T${part('hour')}:${part('minute')}`;
};

export const catDateKey = (value) => catDateTimeInput(value).slice(0, 10);

// datetime-local fields represent CAT wall time regardless of the user's device timezone.
export const catInputToIso = (value) => {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(value || '')) {
    throw new Error('Enter a valid date and time in CAT.');
  }
  return new Date(`${value}+02:00`).toISOString();
};

export const formatCatDateTime = (value) => clinicalDate(value).toLocaleString('en-GB', {
  timeZone: CLINICAL_TIME_ZONE, dateStyle: 'medium', timeStyle: 'short',
}) + ' CAT';

// Internal recurring working hours retain their existing UTC representation.
const shiftClock = (value, hours) => {
  const match = /^(\d{2}):(\d{2})$/.exec(value || '');
  if (!match || Number(match[1]) > 23 || Number(match[2]) > 59) throw new Error('Enter working hours as HH:MM.');
  const shifted = (Number(match[1]) + hours + 24) % 24;
  return `${String(shifted).padStart(2, '0')}:${match[2]}`;
};
export const utcClockToCat = (value) => shiftClock(value, 2);
export const catClockToUtc = (value) => shiftClock(value, -2);
