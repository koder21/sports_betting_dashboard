import React from 'react';
import './SkeletonLoader.css';

export default function SkeletonLoader({
  rows = 5,
  columns = 1,
  type = 'list',
  width = '100%',
  height = '1.2em',
}) {
  const skeletonRows = Array.from({ length: rows });
  return (
    <div className={`skeleton-loader skeleton-${type}`} style={{ width }}>
      {skeletonRows.map((_, idx) => (
        <div key={idx} className="skeleton-row" style={{ height }}>
          {Array.from({ length: columns }).map((_, colIdx) => (
            <div key={colIdx} className="skeleton-block" />
          ))}
        </div>
      ))}
    </div>
  );
}
