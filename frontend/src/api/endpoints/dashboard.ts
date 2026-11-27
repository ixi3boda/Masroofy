import { authorizedRequest } from '../session';
import { DashboardResponse } from '../types';

/** API 11 — `200`. The current month (docs/frontend-api/11-dashboard.md). */
export const getDashboard = (recentLimit: number) =>
  authorizedRequest<DashboardResponse>(`/dashboard?recentLimit=${recentLimit}`, { method: 'GET' });
