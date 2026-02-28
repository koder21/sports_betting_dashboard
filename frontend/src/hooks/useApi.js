// useApi.js
// Reusable hook for API calls with loading/error state
import { useState, useEffect, useCallback, useRef } from 'react';
/**
 * useApi - React hook for async API calls with loading and error state.
 * @template T
 * @param {() => Promise<T>} apiFn - Async function returning data.
 * @param {T} [initial=null] - Initial value for data.
 * @returns {{ data: T, loading: boolean, error: any, refetch: () => Promise<void> }}
 */
export function useApi(apiFn, initial = null) {
  const [data, setData] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const mountedRef = useRef(false);
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFn();
      if (mountedRef.current) setData(result);
    } catch (err) {
      if (mountedRef.current) setError(err);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [apiFn]);
  useEffect(() => {
    mountedRef.current = true;
    fetchData();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);
  return { data, loading, error, refetch: fetchData };
}
export default useApi;