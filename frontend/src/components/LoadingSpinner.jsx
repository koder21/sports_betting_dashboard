import React from 'react';
import './LoadingSpinner.css';

/**
 * Reusable LoadingSpinner component
 * Used across all pages for loading states
 */
const LoadingSpinner = React.memo(({ 
  size = 'medium',
  message = 'Loading...',
  fullPage = false,
}) => {
  const spinnerClass = `loading-spinner loading-spinner-${size}`;
  
  if (fullPage) {
    return (
      <div className="loading-spinner-fullpage">
        <div className={spinnerClass}></div>
        {message && <p className="loading-message">{message}</p>}
      </div>
    );
  }
  
  return (
    <div className="loading-spinner-container">
      <div className={spinnerClass}></div>
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
});

LoadingSpinner.displayName = 'LoadingSpinner';

export default LoadingSpinner;
