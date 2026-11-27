import { getDataSource } from '@/config/env';
import { mockDashboardService } from '@/mocks/services/mockDashboardService';
import { apiDashboardService } from './api/apiDashboardService';
import { DashboardService } from './types';

/**
 * Home dashboard data source: the mock (follows the mock transactions) or the
 * real backend, picked by `EXPO_PUBLIC_DASHBOARD_SOURCE` (else
 * `EXPO_PUBLIC_API_MODE`, else `mock`). Screens only call this.
 */
export const dashboardService: DashboardService =
  getDataSource('dashboard') === 'api' ? apiDashboardService : mockDashboardService;
