// useMetrics.js
// Reusable hook for metrics tracking
import { useEffect } from 'react';
import AnalyticsService from '../services/analytics';

export function useMetrics(pageName) {
  useEffect(() => {
    if (pageName) {
      AnalyticsService.trackPageView(pageName);
    }
  }, [pageName]);
}
