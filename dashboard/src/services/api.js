import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: `${API_URL}`,
  timeout: 10000,
});

export const detectionService = {
  getRecent: (limit = 100, offset = 0) =>
    api.get('/detections', { params: { limit, offset } }),
  
  getBySpecies: (species) =>
    api.get('/detections', { params: { species } }),
};

export const statsService = {
  getStats: (days = 7) =>
    api.get('/stats', { params: { days } }),
  
  getSpecies: (days = 7) =>
    api.get('/species', { params: { days } }),
  
  getConfig: () =>
    api.get('/config'),
};

export const visualizationService = {
  getHeatmap: (days = 7) =>
    api.get('/heatmap', { params: { days } }),
  
  getTrends: (days = 365) =>
    api.get('/trends', { params: { days } }),
};

export default api;
