import { CURRENCY } from '@/constants/app';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/** 30000 → "30,000". Regex-based so output never depends on device locale/Intl support. */
export const formatNumber = (value: number): string =>
  Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ',');

/** 24550 → "EGP 24,550" */
export const formatCurrency = (value: number): string => `${CURRENCY} ${formatNumber(value)}`;

/** -850 → "− EGP 850", 1200 → "+ EGP 1,200" */
export const formatSignedCurrency = (value: number): string =>
  `${value < 0 ? '−' : '+'} ${formatCurrency(Math.abs(value))}`;

/** "2026-10-28" → "28 Oct". Parsed manually to avoid timezone shifts from `new Date(iso)`. */
export const formatDayMonth = (isoDate: string): string => {
  const [, month, day] = isoDate.split('-').map(Number);
  return `${day} ${MONTHS[month - 1]}`;
};

/** "2026-10-28" or "2026-10-28T14:32" → "28 Oct 2026" */
export const formatDate = (isoDate: string): string => {
  const [year, month, day] = isoDate.slice(0, 10).split('-').map(Number);
  return `${day} ${MONTHS[month - 1]} ${year}`;
};

/** "2026-10-28T14:32" → "28 Oct 2026 · 14:32" (local time as written, no timezone conversion). */
export const formatDateTime = (isoDateTime: string): string => `${formatDate(isoDateTime)} · ${isoDateTime.slice(11, 16)}`;

/** "2026-10-28" → "October" */
export const formatMonthName = (isoDate: string): string => MONTH_NAMES[Number(isoDate.slice(5, 7)) - 1];
