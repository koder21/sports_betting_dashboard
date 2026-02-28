// useOddsFormat.js
// Reusable hook for odds format state and event handling
import { useState, useEffect } from 'react';
import { getOddsFormat, setOddsFormat } from '../services/oddsService';

export function useOddsFormat() {
  const [oddsFormat, setOddsFormatState] = useState(getOddsFormat());

  useEffect(() => {
    const handleOddsFormatChange = (e) => {
      setOddsFormatState(e.detail.format);
    };
    window.addEventListener('oddsFormatChanged', handleOddsFormatChange);
    return () => window.removeEventListener('oddsFormatChanged', handleOddsFormatChange);
  }, []);

  const updateOddsFormat = (format) => {
    setOddsFormat(format);
    setOddsFormatState(format);
  };

  return [oddsFormat, updateOddsFormat];
}
