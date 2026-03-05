import axios from 'axios';

const API_BASE_URL = '/api';

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

export const getFundCategories = async () => {
    try {
        const response = await api.get('/categories');
        return response.data.categories || [];
    } catch (error) {
        console.error("Get categories failed", error);
        return [];
    }
};

// Account management
export const getAccounts = async () => {
    try {
        const response = await api.get('/accounts');
        return response.data.accounts || [];
    } catch (error) {
        console.error("Get accounts failed", error);
        return [];
    }
};

export const createAccount = async (data) => {
    return api.post('/accounts', data);
};

export const updateAccount = async (accountId, data) => {
    return api.put(`/accounts/${accountId}`, data);
};

export const deleteAccount = async (accountId) => {
    return api.delete(`/accounts/${accountId}`);
};

// Position management (with account_id)
export const getAccountPositions = async (accountId = 1) => {
    try {
        const response = await api.get('/account/positions', { params: { account_id: accountId } });
        return response.data;
    } catch (error) {
        console.error("Get positions failed", error);
        throw error;
    }
};

export const updatePosition = async (data, accountId = 1) => {
    return api.post('/account/positions', data, { params: { account_id: accountId } });
};

export const deletePosition = async (code, accountId = 1) => {
    return api.delete(`/account/positions/${code}`, { params: { account_id: accountId } });
};

export const addPositionTrade = async (code, data, accountId = 1) => {
    const response = await api.post(`/account/positions/${code}/add`, data, { params: { account_id: accountId } });
    return response.data;
};

export const reducePositionTrade = async (code, data, accountId = 1) => {
    const response = await api.post(`/account/positions/${code}/reduce`, data, { params: { account_id: accountId } });
    return response.data;
};

export const getTransactions = async (accountId = 1, code = null, limit = 100) => {
    const params = { account_id: accountId, limit };
    if (code) params.code = code;
    const response = await api.get('/account/transactions', { params });
    return response.data.transactions || [];
};

export const updatePositionsNav = async (accountId = 1) => {
    return api.post('/account/positions/update-nav', null, { params: { account_id: accountId } });
};

// Get latest NAV data
export const getFundLatestNav = async (fundId) => {
    try {
        const response = await api.get(`/fund/${fundId}/latest-nav`);
        return response.data;
    } catch (error) {
        console.error(`Get latest NAV for ${fundId} failed`, error);
        return null;
    }
};

// Get AI analysis history
export const getAiAnalysisHistory = async (fundCode, limit = 10) => {
    try {
        const response = await api.get(`/ai/analysis_history/${fundCode}`, { params: { limit } });
        console.log('AI analysis history response:', response.data);
        return response.data || [];
    } catch (error) {
        console.error(`Get AI analysis history for ${fundCode} failed`, error);
        return [];
    }
};

// Get user notes
export const getUserNotes = async (fundCode, limit = 10) => {
    try {
        const response = await api.get(`/ai/user_notes/${fundCode}`, { params: { limit } });
        return response.data || [];
    } catch (error) {
        console.error(`Get user notes for ${fundCode} failed`, error);
        return [];
    }
};

// Save user note
export const saveUserNote = async (fundCode, fundName, noteContent, noteDate = null, noteColor = '#10b981') => {
    try {
        const response = await api.post('/ai/user_note', {
            fund_code: fundCode,
            fund_name: fundName,
            note_content: noteContent,
            note_date: noteDate,
            note_color: noteColor
        });
        return response.data;
    } catch (error) {
        console.error('Save user note failed', error);
        return { error: error.message };
    }
};

// Delete user note
export const deleteUserNote = async (noteId) => {
    try {
        const response = await api.delete(`/ai/user_note/${noteId}`);
        return response.data;
    } catch (error) {
        console.error('Delete user note failed', error);
        return { success: false };
    }
};

// Update user note
export const updateUserNote = async (noteId, noteContent, noteColor) => {
    try {
        const response = await api.put(`/ai/user_note/${noteId}`, {
            note_content: noteContent,
            note_color: noteColor
        });
        return response.data;
    } catch (error) {
        console.error('Update user note failed', error);
        return { error: error.message };
    }
};

// Messages API
export const getMessages = async (msgType = null, limit = 20, offset = 0) => {
    try {
        const params = { limit, offset };
        if (msgType) params.msg_type = msgType;
        const response = await api.get('/messages', { params });
        return response.data;
    } catch (error) {
        console.error('Get messages failed', error);
        return { messages: [], total: 0 };
    }
};

export const getMessage = async (messageId) => {
    try {
        const response = await api.get(`/messages/${messageId}`);
        return response.data;
    } catch (error) {
        console.error('Get message failed', error);
        return { error: error.message };
    }
};

export const markMessageAsRead = async (messageId) => {
    try {
        const response = await api.put(`/messages/${messageId}/read`);
        return response.data;
    } catch (error) {
        console.error('Mark message as read failed', error);
        return { success: false };
    }
};

export const markAllMessagesAsRead = async (msgType = null) => {
    try {
        const params = msgType ? { msg_type: msgType } : {};
        const response = await api.put('/messages/read_all', null, { params });
        return response.data;
    } catch (error) {
        console.error('Mark all messages as read failed', error);
        return { success: false };
    }
};

export const deleteMessage = async (messageId) => {
    try {
        const response = await api.delete(`/messages/${messageId}`);
        return response.data;
    } catch (error) {
        console.error('Delete message failed', error);
        return { success: false };
    }
};

export const getUnreadMessageCount = async (msgType = null) => {
    try {
        const params = msgType ? { msg_type: msgType } : {};
        const response = await api.get('/messages/unread_count', { params });
        return response.data;
    } catch (error) {
        console.error('Get unread count failed', error);
        return { count: 0 };
    }
};
