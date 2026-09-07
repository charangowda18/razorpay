const API_BASE = '';

const api = {
    
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

    
    async getDashboardStats() {
        return this.request('/api/analytics/dashboard');
    },

    
    async getMerchants() {
        return this.request('/api/analytics/merchants');
    },

    
    async getModelInfo() {
        return this.request('/api/analytics/model-info');
    },

    
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

    
    async getTransaction(transactionId) {
        return this.request(`/api/transactions/${transactionId}`);
    },

    
    async evaluateTransaction(transactionId) {
        return this.request(`/api/recovery/evaluate/${transactionId}`);
    },

    
    async triggerRecovery(transactionId) {
        return this.request(`/api/recovery/trigger/${transactionId}`, {
            method: 'POST',
        });
    },

    
    async executeRetry(transactionId, retryId) {
        return this.request(`/api/recovery/execute-retry/${transactionId}/${retryId}`, {
            method: 'POST',
        });
    },

    
    async getRecoveryOpportunities(limit = 20) {
        return this.request(`/api/recovery/opportunities?limit=${limit}`);
    },

    
    async getInsights(merchantId = null) {
        const query = merchantId ? `?merchant_id=${merchantId}` : '';
        return this.request(`/api/recovery/insights${query}`);
    },

    
    async healthCheck() {
        return this.request('/health');
    },
};
