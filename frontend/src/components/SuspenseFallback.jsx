import React, { Suspense } from 'react';

export default function SuspenseFallback({ message = 'Loading...' }) {
  return (
    <div className="suspense-fallback" role="status" aria-live="polite">
      <span>{message}</span>
    </div>
  );
}
