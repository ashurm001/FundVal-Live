import axios from 'axios';

const API_BASE_URL = 'http://localhost:21345/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const searchFunds = async (query) => {
  try {
    const response = await api.get('/search', { params: { q: query } });
    return response.data;
  } catch (error) {
    console.error("Search failed", error);
    return [];
  }
};

export const getFundDetail = async (fundId) => {
  try {
    const response = await api.get(`/fund/${fundId}`);
    return response.data;
  } catch (error) {
    console.error(`Get fund ${fundId} failed`, error);
    throw error;
  }
};

export const getFundHistory = async (fundId, limit = 30) => {
    try {
        const response = await api.get(`/fund/${fundId}/history`, { params: { limit } });
        return response.data;
    } catch (error) {
        console.error("Get history failed", error);
        return [];
    }
};

export const subscribeFund = async (fundId, data) => {
    return api.post(`/fund/${fundId}/subscribe`, data);
};
