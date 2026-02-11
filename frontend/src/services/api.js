import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  // No timeout - long-running operations (injuries, etc) can take 5+ minutes
});

export default api;