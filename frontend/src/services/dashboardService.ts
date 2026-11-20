import { mockDashboardSummary } from '@/mocks/data/dashboard';
import { DashboardSummary } from '@/types/dashboard';

/**
 * Home dashboard data source. Returns the mock summary for now; replace the
 * body when the backend is ready — the dashboard screen only calls this.
 */
export const dashboardService = {
  getSummary: (): DashboardSummary => mockDashboardSummary,
};
