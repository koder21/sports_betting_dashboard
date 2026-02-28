// useLoading.js
// Reusable hook for loading state management
import { useState } from 'react';

export function useLoading(initial = false) {
  const [loading, setLoading] = useState(initial);
  const startLoading = () => setLoading(true);
  const stopLoading = () => setLoading(false);
  return { loading, startLoading, stopLoading };
}
