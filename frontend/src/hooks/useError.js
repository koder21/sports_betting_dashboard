// useError.js
// Reusable hook for error state management
import React, { useState } from 'react';

export function useError(initial = null) {
  const [error, setError] = useState(initial);
  const setErrorMsg = React.useCallback((msg) => setError(msg), []);
  const clearError = React.useCallback(() => setError(null), []);
  return { error, setErrorMsg, clearError };
}
