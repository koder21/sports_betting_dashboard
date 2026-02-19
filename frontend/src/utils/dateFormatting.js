/**
 * Shared Date Formatting Utilities
 * Used across all pages for consistent date/time display
 */

import { convertToUserTimezone } from '../services/timezoneService.js';

/**
 * Format a date string for display
 * @param {string|Date} dateString - Date to format
 * @param {string} format - Format type: 'date', 'time', 'datetime', 'relative'
 * @returns {string} Formatted date string
 */
export const formatDate = (dateString, format = 'date') => {
  if (!dateString) return '';
  
  try {
    return convertToUserTimezone(dateString, format);
  } catch (error) {
    console.error('Date formatting error:', error);
    return String(dateString);
  }
};

/**
 * Format a date for display in user's timezone (shorthand)
 * @param {string|Date} dateString - Date to format
 * @returns {string} Formatted date string
 */
export const formatDateTime = (dateString) => {
  return formatDate(dateString, 'datetime');
};

/**
 * Format a time for display in user's timezone
 * @param {string|Date} dateString - Date to format
 * @returns {string} Formatted time string
 */
export const formatTime = (dateString) => {
  return formatDate(dateString, 'time');
};

/**
 * Format a date as relative time (e.g., "2 hours ago", "in 3 days")
 * @param {string|Date} dateString - Date to format
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (dateString) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    // Future dates
    if (diffMs < 0) {
      const absDays = Math.abs(diffDays);
      const absHours = Math.abs(diffHours);
      const absMins = Math.abs(diffMins);
      
      if (absDays > 0) return `in ${absDays} day${absDays !== 1 ? 's' : ''}`;
      if (absHours > 0) return `in ${absHours} hour${absHours !== 1 ? 's' : ''}`;
      if (absMins > 0) return `in ${absMins} minute${absMins !== 1 ? 's' : ''}`;
      return 'in a moment';
    }

    // Past dates
    if (diffDays > 7) {
      return formatDate(dateString, 'date');
    }
    if (diffDays > 0) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    if (diffHours > 0) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffMins > 0) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    return 'just now';
  } catch (error) {
    console.error('Relative time formatting error:', error);
    return formatDate(dateString, 'date');
  }
};

/**
 * Group items by date (useful for grouping bets/games by day)
 * @param {Array} items - Items with a date property
 * @param {string} dateKey - Property name containing the date
 * @returns {Object} Object with dates as keys, items as values
 */
export const groupByDate = (items, dateKey = 'placed_at') => {
  if (!items || items.length === 0) return {};
  
  const groups = {};
  
  items.forEach((item) => {
    const dateStr = item[dateKey];
    if (!dateStr) return;
    
    try {
      const date = new Date(dateStr);
      const dateOnly = date.toISOString().split('T')[0]; // YYYY-MM-DD
      
      if (!groups[dateOnly]) {
        groups[dateOnly] = [];
      }
      groups[dateOnly].push(item);
    } catch (error) {
      console.error('Date grouping error:', error);
    }
  });
  
  return groups;
};

/**
 * Sort items by date
 * @param {Array} items - Items with a date property
 * @param {string} dateKey - Property name containing the date
 * @param {string} direction - 'asc' or 'desc'
 * @returns {Array} Sorted items
 */
export const sortByDate = (items, dateKey = 'placed_at', direction = 'desc') => {
  if (!items || items.length === 0) return [];
  
  return [...items].sort((a, b) => {
    const dateA = new Date(a[dateKey]);
    const dateB = new Date(b[dateKey]);
    
    if (isNaN(dateA.getTime()) || isNaN(dateB.getTime())) {
      return 0;
    }
    
    return direction === 'desc' ? dateB - dateA : dateA - dateB;
  });
};

/**
 * Check if a date is today
 * @param {string|Date} dateString - Date to check
 * @returns {boolean} True if date is today
 */
export const isToday = (dateString) => {
  if (!dateString) return false;
  
  try {
    const date = new Date(dateString);
    const today = new Date();
    
    return date.toDateString() === today.toDateString();
  } catch (error) {
    return false;
  }
};

/**
 * Check if a date is in the past
 * @param {string|Date} dateString - Date to check
 * @returns {boolean} True if date is in the past
 */
export const isPast = (dateString) => {
  if (!dateString) return false;
  
  try {
    const date = new Date(dateString);
    const now = new Date();
    
    return date < now;
  } catch (error) {
    return false;
  }
};

/**
 * Get a friendly date label (e.g., "Today", "Yesterday", "Jan 15")
 * @param {string|Date} dateString - Date to format
 * @returns {string} Friendly date label
 */
export const getFriendlyDateLabel = (dateString) => {
  if (!dateString) return '';
  try {
    // Convert to user's timezone for correct day comparison
    const userDate = new Date(convertToUserTimezone(dateString, 'iso'));
    // Always use 'Month Day' format (e.g., 'Feb 11')
    return userDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch (error) {
    console.error('Friendly date label error:', error);
    return formatDate(dateString, 'date');
  }
};
