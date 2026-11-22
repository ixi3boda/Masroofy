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

/** 1250.5 → "1,250.50". Regex-based so output never depends on device locale/Intl support. */
export const formatExactNumber = (value: number): string => {
  const [whole, piastres] = value.toFixed(2).split('.');
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${piastres}`;
};

/** 30000 → "30,000", 850.5 → "850.50": piastres show only when there are some. */
export const formatNumber = (value: number): string => formatExactNumber(value).replace(/\.00$/, '');

/** 24550 → "EGP 24,550" */
export const formatCurrency = (value: number): string => `${CURRENCY} ${formatNumber(value)}`;

/** 850 → "EGP 850.00", for confirmations that need the exact amount. */
export const formatExactCurrency = (value: number): string => `${CURRENCY} ${formatExactNumber(value)}`;

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

/** "28 Oct 2026" or "28 October 2026" → "2026-10-28". `null` unless it is a real date. */
export const parseDate = (text: string): string | null => {
  const parts = text.trim().match(/^(\d{1,2})\s+([a-z]{3,})\s+([12]\d{3})$/i);
  if (!parts) return null;
  const [, dayText, monthText, year] = parts;
  const day = Number(dayText);
  const month = MONTH_NAMES.findIndex((name) => name.toLowerCase().startsWith(monthText.toLowerCase())) + 1;
  // Day 0 of the next month is the last day of this one.
  if (!month || day < 1 || day > new Date(Date.UTC(Number(year), month, 0)).getUTCDate()) return null;
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
};

/** "2026-10-28T14:32" → "28 Oct 2026 · 14:32" (local time as written, no timezone conversion). */
export const formatDateTime = (isoDateTime: string): string => `${formatDate(isoDateTime)} · ${isoDateTime.slice(11, 16)}`;

/** "2026-10-28" → "October" */
export const formatMonthName = (isoDate: string): string => MONTH_NAMES[Number(isoDate.slice(5, 7)) - 1];

/** "2026-10-28" → "October 2026" */
export const formatMonthYear = (isoDate: string): string => `${formatMonthName(isoDate)} ${isoDate.slice(0, 4)}`;

/** "2026-10-28" → "28 October 2026" */
export const formatLongDate = (isoDate: string): string => `${Number(isoDate.slice(8, 10))} ${formatMonthYear(isoDate)}`;

/** "1–28 Oct 2026" within a month, otherwise "28 Sep 2026 – 3 Oct 2026". */
export const formatDateRange = (from: string, to: string): string => {
  if (from === to) return formatDate(from);
  if (from.slice(0, 7) === to.slice(0, 7)) return `${Number(from.slice(8, 10))}–${formatDate(to)}`;
  return `${formatDate(from)} – ${formatDate(to)}`;
};
