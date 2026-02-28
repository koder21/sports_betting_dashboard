import axios from 'axios';

const api = axios.create({
  baseURL: '/api', // Prefix all API calls for Vite proxy
});

export default api;
