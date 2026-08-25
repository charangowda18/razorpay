/**
 * API Client — Handles all communication with the FastAPI backend.
 * 
 * Design: Centralized API module so all endpoints are in one place.
 * Makes it easy to swap the base URL for deployment.
 */

const API_BASE = '';  // Same origin (empty string = relative to current host)

const api = {
    /**
     * Generic fetch wrapper with error handling.
     */
    async request(endpoint, options = {}) {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
                ...options,
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    // ======== Analytics ========

    /** Get all dashboard statistics */
    async getDashboardStats() {
        return this.request('/api/analytics/dashboard');
    },

    /** Get merchant list with stats */
    async getMerchants() {
        return this.request('/api/analytics/merchants');
    },

    /** Get ML model info */
    async getModelInfo() {
        return this.request('/api/analytics/model-info');
    },

    // ======== Transactions ========

    /** Get failed transactions with optional filters */
    async getFailedTransactions(params = {}) {
        const query = new URLSearchParams();
        if (params.limit) query.set('limit', params.limit);
        if (params.offset) query.set('offset', params.offset);
        if (params.failure_reason) query.set('failure_reason', params.failure_reason);
        if (params.bank_name) query.set('bank_name', params.bank_name);
        if (params.payment_method) query.set('payment_method', params.payment_method);
        if (params.sort_by) query.set('sort_by', params.sort_by);
        if (params.sort_order) query.set('sort_order', params.sort_order);

        const queryStr = query.toString();
        return this.request(`/api/transactions/failed${queryStr ? '?' + queryStr : ''}`);
    },

    /** Get single transaction details */
    async getTransaction(transactionId) {
        return this.request(`/api/transactions/${transactionId}`);
    },

    // ======== Recovery ========

    /** Evaluate a transaction's retry score */
    async evaluateTransaction(transactionId) {
        return this.request(`/api/recovery/evaluate/${transactionId}`);
    },

    /** Trigger full recovery flow */
    async triggerRecovery(transactionId) {
        return this.request(`/api/recovery/trigger/${transactionId}`, {
            method: 'POST',
        });
    },

    /** Execute a retry attempt */
    async executeRetry(transactionId, retryId) {
        return this.request(`/api/recovery/execute-retry/${transactionId}/${retryId}`, {
            method: 'POST',
        });
    },

    /** Get top recovery opportunities */
    async getRecoveryOpportunities(limit = 20) {
        return this.request(`/api/recovery/opportunities?limit=${limit}`);
    },

    /** Get AI-generated insights */
    async getInsights(merchantId = null) {
        const query = merchantId ? `?merchant_id=${merchantId}` : '';
        return this.request(`/api/recovery/insights${query}`);
    },

    // ======== Health ========

    /** Check system health */
    async healthCheck() {
        return this.request('/health');
    },
};
