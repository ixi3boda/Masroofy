const CURRENCY = 'EGP';
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

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
