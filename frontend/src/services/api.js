import axios from 'axios';

const api = axios.create({
  // In production (Railway), set VITE_API_URL to your backend Railway URL
  // e.g. https://your-backend.up.railway.app
  // Locally, Vite proxy forwards /api to localhost:8000
  baseURL: import.meta.env.VITE_API_URL || '',
});

export default api;
