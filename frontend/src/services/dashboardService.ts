import { mockDashboardService } from '@/mocks/services/mockDashboardService';
import { DashboardService } from './types';

/**
 * Home dashboard data source. The mock follows the mock transactions; swap in
 * an `api` implementation here when the backend is ready — screens only call this.
 */
export const dashboardService: DashboardService = mockDashboardService;
