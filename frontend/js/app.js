/**
 * Main Application — Orchestrates the dashboard UI.
 * 
 * Handles: Tab navigation, data loading, table rendering, 
 * user interactions, toast notifications, and modals.
 */

// ============================================================
// STATE
// ============================================================

const state = {
    currentTab: 'overview',
    transactions: {
        data: [],
        total: 0,
        page: 1,
        limit: 20,
    },
    dashboardData: null,
    opportunities: null,
    merchants: null,
};

// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    setupTabNavigation();
    setupFilters();
    setupButtons();
    await checkSystemHealth();
    await loadDashboardData();
});

// ============================================================
// SYSTEM HEALTH CHECK
// ============================================================

async function checkSystemHealth() {
    try {
        const health = await api.healthCheck();
        const aiStatus = document.getElementById('ai-status');
        if (health.ai_available) {
            aiStatus.textContent = '🤖 AI: Connected';
            aiStatus.style.borderColor = 'rgba(16, 185, 129, 0.3)';
            aiStatus.style.color = '#10b981';
            aiStatus.style.background = 'rgba(16, 185, 129, 0.1)';
        } else {
            aiStatus.textContent = '🤖 AI: Offline';
            aiStatus.style.borderColor = 'rgba(245, 158, 11, 0.3)';
            aiStatus.style.color = '#f59e0b';
            aiStatus.style.background = 'rgba(245, 158, 11, 0.1)';
        }
    } catch (e) {
        const aiStatus = document.getElementById('ai-status');
        aiStatus.textContent = '🤖 AI: Error';
        aiStatus.style.color = '#ef4444';
    }
}

// ============================================================
// TAB NAVIGATION
// ============================================================

function setupTabNavigation() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

function switchTab(tabName) {
    state.currentTab = tabName;

    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`content-${tabName}`).classList.add('active');

    // Load data for the tab
    switch (tabName) {
        case 'overview':
            loadDashboardData();
            break;
        case 'transactions':
            loadTransactions();
            break;
        case 'recovery':
            loadOpportunities();
            break;
        case 'insights':
            loadModelInfo();
            break;
        case 'merchants':
            loadMerchants();
            break;
    }
}

// ============================================================
// FILTERS
// ============================================================

function setupFilters() {
    ['filter-failure-reason', 'filter-payment-method', 'filter-bank'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                state.transactions.page = 1;
                loadTransactions();
            });
        }
    });
}

// ============================================================
// BUTTONS
// ============================================================

function setupButtons() {
    // Pagination
    document.getElementById('btn-prev-page')?.addEventListener('click', () => {
        if (state.transactions.page > 1) {
            state.transactions.page--;
            loadTransactions();
        }
    });

    document.getElementById('btn-next-page')?.addEventListener('click', () => {
        const totalPages = Math.ceil(state.transactions.total / state.transactions.limit);
        if (state.transactions.page < totalPages) {
            state.transactions.page++;
            loadTransactions();
        }
    });

    // Recovery opportunities refresh
    document.getElementById('btn-refresh-opportunities')?.addEventListener('click', () => {
        loadOpportunities();
        showToast('Refreshing recovery scores...', 'info');
    });

    // AI Insights
    document.getElementById('btn-generate-insights')?.addEventListener('click', () => {
        generateInsights();
    });
}

// ============================================================
// DATA LOADING — OVERVIEW
// ============================================================

async function loadDashboardData() {
    try {
        const data = await api.getDashboardStats();
        state.dashboardData = data;
        renderOverviewStats(data.overview);
        renderDailyTrendChart(data.daily_trend);
        renderFailureReasonsChart(data.failure_breakdown);
        renderBankChart(data.bank_stats);
        renderHourlyChart(data.hourly_pattern);
    } catch (error) {
        showToast('Failed to load dashboard data', 'error');
        console.error('Dashboard error:', error);
    }
}

function renderOverviewStats(overview) {
    document.getElementById('stat-success-amount').textContent = `₹${formatCurrency(overview.success_amount)}`;
    document.getElementById('stat-success-count').textContent = overview.success_count?.toLocaleString() || '0';
    document.getElementById('stat-failed-amount').textContent = `₹${formatCurrency(overview.failed_amount)}`;
    document.getElementById('stat-failed-count').textContent = overview.failed_count?.toLocaleString() || '0';
    document.getElementById('stat-recovered-amount').textContent = `₹${formatCurrency(overview.recovered_amount)}`;
    document.getElementById('stat-recovery-rate').textContent = `${overview.recovery_rate || 0}%`;
    document.getElementById('stat-potential-amount').textContent = `₹${formatCurrency(overview.potential_recovery)}`;

    // Show recovery count breakdown for clarity
    const totalFailed = (overview.failed_count || 0) + (overview.recovered_count || 0);
    const countsEl = document.getElementById('stat-recovery-counts');
    if (countsEl) {
        countsEl.textContent = `${overview.recovered_count || 0} of ${totalFailed} failed txns`;
    }
}

// ============================================================
// DATA LOADING — TRANSACTIONS
// ============================================================

async function loadTransactions() {
    const failureReason = document.getElementById('filter-failure-reason')?.value;
    const paymentMethod = document.getElementById('filter-payment-method')?.value;
    const bankName = document.getElementById('filter-bank')?.value;

    try {
        const data = await api.getFailedTransactions({
            limit: state.transactions.limit,
            offset: (state.transactions.page - 1) * state.transactions.limit,
            failure_reason: failureReason || undefined,
            payment_method: paymentMethod || undefined,
            bank_name: bankName || undefined,
            sort_by: 'amount',
            sort_order: 'desc',
        });

        state.transactions.data = data.transactions;
        state.transactions.total = data.total;
        renderTransactionsTable(data.transactions);
        renderPagination();
    } catch (error) {
        showToast('Failed to load transactions', 'error');
    }
}

function renderTransactionsTable(transactions) {
    const tbody = document.getElementById('transactions-tbody');
    if (!tbody) return;

    if (transactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-state" style="padding: 40px; text-align: center;">
                    <p style="color: var(--text-muted);">No transactions found matching filters.</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = transactions.map(txn => {
        const retryScore = txn.retry_score != null ? txn.retry_score : null;
        const scoreClass = retryScore >= 0.7 ? 'high' : retryScore >= 0.4 ? 'medium' : 'low';
        const statusBadge = getStatusBadge(txn.status);
        const date = new Date(txn.created_at).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: '2-digit',
        });

        return `
            <tr>
                <td class="txn-id">${txn.id.substring(0, 20)}...</td>
                <td class="amount">₹${Number(txn.amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                <td>${statusBadge}</td>
                <td>${formatFailureReason(txn.failure_reason)}</td>
                <td>${txn.payment_method?.toUpperCase() || '-'}</td>
                <td>${txn.bank_name || '-'}</td>
                <td>
                    ${retryScore != null ? `
                        <div class="score-bar-container">
                            <div class="score-bar">
                                <div class="score-bar-fill ${scoreClass}" style="width: ${retryScore * 100}%"></div>
                            </div>
                            <span class="score-value" style="color: var(--${scoreClass === 'high' ? 'success' : scoreClass === 'medium' ? 'warning' : 'danger'})">${(retryScore * 100).toFixed(0)}%</span>
                        </div>
                    ` : '<span style="color: var(--text-muted)">—</span>'}
                </td>
                <td style="color: var(--text-muted); font-size: 0.78rem;">${date}</td>
                <td>
                    ${txn.status === 'failed' ? `
                        <button class="btn btn-primary btn-sm" onclick="handleRecovery('${txn.id}')">
                            🔄 Recover
                        </button>
                    ` : ''}
                </td>
            </tr>
        `;
    }).join('');
}

function renderPagination() {
    const totalPages = Math.ceil(state.transactions.total / state.transactions.limit);
    document.getElementById('page-info').textContent =
        `Page ${state.transactions.page} of ${totalPages} (${state.transactions.total} transactions)`;
    document.getElementById('btn-prev-page').disabled = state.transactions.page <= 1;
    document.getElementById('btn-next-page').disabled = state.transactions.page >= totalPages;
}

// ============================================================
// DATA LOADING — RECOVERY OPPORTUNITIES
// ============================================================

async function loadOpportunities() {
    try {
        const data = await api.getRecoveryOpportunities(20);
        state.opportunities = data;
        document.getElementById('opp-count').textContent = data.total_evaluated || 0;
        document.getElementById('opp-amount').textContent = `₹${formatCurrency(data.total_recoverable_amount)}`;
        renderOpportunities(data.opportunities);
    } catch (error) {
        showToast('Failed to load recovery opportunities', 'error');
    }
}

function renderOpportunities(opportunities) {
    const grid = document.getElementById('opportunities-grid');
    if (!grid) return;

    if (!opportunities || opportunities.length === 0) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🎯</div><p>No recovery opportunities found.</p></div>';
        return;
    }

    grid.innerHTML = opportunities.map(opp => {
        const scoreClass = opp.retry_score >= 0.7 ? 'high' : opp.retry_score >= 0.4 ? 'medium' : 'low';
        const badgeClass = opp.confidence === 'high' ? 'badge-success' :
                          opp.confidence === 'medium' ? 'badge-pending' : 'badge-failed';

        return `
            <div class="opportunity-card" onclick="handleRecovery('${opp.transaction_id}')">
                <div class="opp-header">
                    <span class="opp-amount">₹${Number(opp.amount).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                    <span class="badge ${badgeClass}">${opp.confidence} confidence</span>
                </div>
                <div class="opp-details">
                    <div class="opp-detail">
                        <span class="opp-detail-label">Failure Reason</span>
                        <span class="opp-detail-value">${formatFailureReason(opp.failure_reason)}</span>
                    </div>
                    <div class="opp-detail">
                        <span class="opp-detail-label">Payment Method</span>
                        <span class="opp-detail-value">${opp.payment_method?.toUpperCase()}</span>
                    </div>
                    <div class="opp-detail">
                        <span class="opp-detail-label">Bank</span>
                        <span class="opp-detail-value">${opp.bank_name}</span>
                    </div>
                    <div class="opp-detail">
                        <span class="opp-detail-label">AI Retry Score</span>
                        <span class="opp-detail-value">
                            <div class="score-bar-container">
                                <div class="score-bar">
                                    <div class="score-bar-fill ${scoreClass}" style="width: ${opp.retry_score * 100}%"></div>
                                </div>
                                <span class="score-value" style="color: var(--${scoreClass === 'high' ? 'success' : scoreClass === 'medium' ? 'warning' : 'danger'})">${(opp.retry_score * 100).toFixed(0)}%</span>
                            </div>
                        </span>
                    </div>
                </div>
                <div class="opp-reason">${opp.reason}</div>
                <button class="btn btn-primary" style="width: 100%;">
                    🔄 Trigger Recovery
                </button>
            </div>
        `;
    }).join('');
}

// ============================================================
// DATA LOADING — AI INSIGHTS
// ============================================================

async function generateInsights() {
    const btn = document.getElementById('btn-generate-insights');
    const content = document.getElementById('insights-content');

    btn.disabled = true;
    btn.textContent = '⏳ Analyzing...';

    content.innerHTML = `
        <div class="insight-card">
            <div class="loading-skeleton loading-text" style="width: 80%;"></div>
            <div class="loading-skeleton loading-text" style="width: 60%;"></div>
            <div class="loading-skeleton loading-text short"></div>
        </div>
    `;

    try {
        const data = await api.getInsights();
        renderInsights(data);
        showToast('AI analysis complete!', 'success');
    } catch (error) {
        content.innerHTML = `
            <div class="insight-card">
                <div class="insight-severity critical">Error</div>
                <div class="insight-text">Failed to generate insights. ${error.message}</div>
            </div>
        `;
        showToast('Failed to generate insights', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '✨ Generate New Insights';
    }
}

function renderInsights(data) {
    const content = document.getElementById('insights-content');
    const analysis = data.analysis || {};

    let html = '';

    // Summary
    if (analysis.summary) {
        html += `
            <div class="insight-card">
                <div class="insight-severity ${analysis.risk_score >= 7 ? 'critical' : analysis.risk_score >= 4 ? 'warning' : 'info'}">
                    ${analysis.risk_score >= 7 ? '🔴 Critical' : analysis.risk_score >= 4 ? '🟡 Warning' : '🔵 Info'}
                    ${analysis.risk_score ? ` — Risk Score: ${analysis.risk_score}/10` : ''}
                </div>
                <div class="insight-text">${analysis.summary}</div>
                ${analysis.estimated_recoverable_percentage ? `
                    <div style="margin-top: 12px; padding: 8px 12px; background: rgba(139, 92, 246, 0.1); border-radius: 8px; font-size: 0.85rem;">
                        💡 <strong>Estimated ${analysis.estimated_recoverable_percentage}%</strong> of failed transactions are recoverable
                    </div>
                ` : ''}
            </div>
        `;
    }

    // Patterns
    if (analysis.patterns && analysis.patterns.length > 0) {
        html += `<h3 style="font-size: 0.9rem; color: var(--text-secondary); margin: 16px 0 12px; font-weight: 600;">📋 Detected Patterns</h3>`;
        analysis.patterns.forEach(pattern => {
            html += `
                <div class="insight-card">
                    <div class="insight-severity ${pattern.severity || 'info'}">${pattern.severity?.toUpperCase() || 'INFO'}</div>
                    <div class="insight-text">${pattern.pattern}</div>
                    ${pattern.affected_transactions ? `
                        <div style="margin-top: 8px; font-size: 0.78rem; color: var(--text-muted);">
                            Affected: ${pattern.affected_transactions} transactions
                            ${pattern.potential_recovery ? ` | Potential recovery: ${pattern.potential_recovery}` : ''}
                        </div>
                    ` : ''}
                </div>
            `;
        });
    }

    // Recommendations
    if (analysis.recommendations && analysis.recommendations.length > 0) {
        html += `
            <div class="insight-card">
                <div class="insight-severity info">💡 AI Recommendations</div>
                <ul class="insight-recommendations">
                    ${analysis.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    // Transactions analyzed count
    html += `
        <div style="text-align: center; padding: 12px; color: var(--text-muted); font-size: 0.78rem;">
            Analysis based on ${data.transactions_analyzed || 0} recent failed transactions
            ${data.ai_available ? ' • Powered by Gemini AI' : ' • Using rule-based analysis'}
        </div>
    `;

    content.innerHTML = html;
}

async function loadModelInfo() {
    try {
        const info = await api.getModelInfo();
        if (info.top_features) {
            renderFeatureImportanceChart(info);
        }
    } catch (error) {
        console.log('Model info not available yet');
    }
}

// ============================================================
// DATA LOADING — MERCHANTS
// ============================================================

async function loadMerchants() {
    try {
        const merchants = await api.getMerchants();
        state.merchants = merchants;
        renderMerchantsTable(merchants);
    } catch (error) {
        showToast('Failed to load merchants', 'error');
    }
}

function renderMerchantsTable(merchants) {
    const tbody = document.getElementById('merchants-tbody');
    if (!tbody) return;

    tbody.innerHTML = merchants.map(m => {
        const totalFailed = (m.failed_count || 0) + (m.recovered_count || 0);
        const recoveryRate = totalFailed > 0
            ? ((m.recovered_count || 0) / totalFailed * 100).toFixed(1)
            : '0.0';
        const recoveryClass = recoveryRate >= 50 ? 'green' : recoveryRate >= 30 ? 'yellow' : 'red';

        return `
            <tr>
                <td style="font-weight: 600; color: var(--text-primary);">${m.name}</td>
                <td><span class="badge badge-pending" style="text-transform: capitalize;">${m.business_type?.replace(/_/g, ' ')}</span></td>
                <td>${(m.total_transactions || 0).toLocaleString()}</td>
                <td style="color: var(--success);">${(m.success_count || 0).toLocaleString()}</td>
                <td style="color: var(--danger);">${(m.failed_count || 0).toLocaleString()}</td>
                <td style="color: var(--recovered);">${(m.recovered_count || 0).toLocaleString()}</td>
                <td class="amount">₹${formatCurrency(m.total_revenue)}</td>
                <td style="color: var(--danger);">₹${formatCurrency(m.failed_amount)}</td>
                <td>
                    <span class="highlight ${recoveryClass}" style="font-weight: 700;">${recoveryRate}%</span>
                </td>
            </tr>
        `;
    }).join('');
}

// ============================================================
// RECOVERY ACTIONS
// ============================================================

async function handleRecovery(transactionId) {
    showToast('🤖 Running AI recovery analysis...', 'info');

    try {
        const result = await api.triggerRecovery(transactionId);
        showRecoveryModal(result);
        showToast('Recovery analysis complete!', 'success');

        // Refresh data
        if (state.currentTab === 'transactions') loadTransactions();
        if (state.currentTab === 'recovery') loadOpportunities();
    } catch (error) {
        showToast(`Recovery failed: ${error.message}`, 'error');
    }
}

function showRecoveryModal(result) {
    const evaluation = result.evaluation || {};
    const aiStrategy = result.ai_strategy || {};
    const retryScheduled = result.retry_scheduled;

    const scoreClass = evaluation.retry_score >= 0.7 ? 'high' : evaluation.retry_score >= 0.4 ? 'medium' : 'low';
    const scoreColor = scoreClass === 'high' ? '#10b981' : scoreClass === 'medium' ? '#f59e0b' : '#ef4444';

    let stepsHtml = '';
    if (aiStrategy.steps && aiStrategy.steps.length > 0) {
        stepsHtml = aiStrategy.steps.map(step => `
            <div style="display: flex; gap: 12px; margin-bottom: 12px; padding: 10px; background: var(--bg-glass); border-radius: 8px;">
                <div style="min-width: 28px; height: 28px; background: var(--gradient-primary); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700;">${step.step}</div>
                <div>
                    <div style="font-size: 0.85rem; color: var(--text-primary); font-weight: 500;">${step.action}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
                        ${step.timing ? `⏰ ${step.timing}` : ''} 
                        ${step.expected_success_rate ? `• 📈 ${step.expected_success_rate}` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    }

    const modalHtml = `
        <div class="modal-overlay" onclick="closeModal(event)">
            <div class="modal" onclick="event.stopPropagation()">
                <div class="modal-title">
                    <span>🤖 AI Recovery Analysis</span>
                    <button class="modal-close" onclick="closeModal()">&times;</button>
                </div>

                <!-- Retry Score -->
                <div style="text-align: center; padding: 20px; margin-bottom: 20px; background: var(--bg-glass); border-radius: 12px;">
                    <div style="font-size: 2.5rem; font-weight: 800; color: ${scoreColor};">
                        ${(evaluation.retry_score * 100).toFixed(0)}%
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">
                        Retry Success Probability
                    </div>
                    <div style="margin-top: 8px;">
                        <span class="badge badge-${evaluation.confidence === 'high' ? 'success' : evaluation.confidence === 'medium' ? 'pending' : 'failed'}">
                            ${evaluation.confidence} confidence
                        </span>
                    </div>
                </div>

                <!-- Evaluation Details -->
                <div style="margin-bottom: 16px;">
                    <div style="font-size: 0.85rem; color: var(--text-secondary); padding: 10px; background: var(--bg-glass); border-radius: 8px;">
                        ${evaluation.reason || 'No additional details.'}
                    </div>
                </div>

                <!-- Retry Scheduled -->
                ${retryScheduled && retryScheduled.scheduled ? `
                    <div style="padding: 12px; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; margin-bottom: 16px;">
                        <div style="font-size: 0.85rem; color: var(--success); font-weight: 600;">
                            ✅ Smart Retry Scheduled
                        </div>
                        <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">
                            Attempt #${retryScheduled.attempt_number} scheduled for ${new Date(retryScheduled.scheduled_time).toLocaleString('en-IN')}
                        </div>
                    </div>
                ` : ''}

                <!-- AI Strategy -->
                ${aiStrategy.strategy_summary ? `
                    <div style="margin-bottom: 16px;">
                        <div style="font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;">📋 AI Recovery Strategy</div>
                        <div style="font-size: 0.83rem; color: var(--text-secondary); margin-bottom: 12px;">
                            ${aiStrategy.strategy_summary}
                        </div>
                        ${stepsHtml}
                    </div>
                ` : ''}

                <!-- Customer Message -->
                ${aiStrategy.customer_message ? `
                    <div style="padding: 12px; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 8px; margin-bottom: 16px;">
                        <div style="font-size: 0.78rem; font-weight: 600; color: var(--accent-blue); margin-bottom: 6px;">💬 Suggested Customer Message</div>
                        <div style="font-size: 0.83rem; color: var(--text-secondary); font-style: italic;">
                            "${aiStrategy.customer_message}"
                        </div>
                    </div>
                ` : ''}

                <button class="btn btn-primary" style="width: 100%; margin-top: 8px;" onclick="closeModal()">
                    Close
                </button>
            </div>
        </div>
    `;

    document.getElementById('modal-container').innerHTML = modalHtml;
}

function closeModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('modal-container').innerHTML = '';
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// ============================================================
// UTILITIES
// ============================================================

function formatCurrency(amount) {
    if (!amount) return '0';
    const num = Number(amount);
    if (num >= 10000000) return (num / 10000000).toFixed(2) + ' Cr';
    if (num >= 100000) return (num / 100000).toFixed(2) + ' L';
    if (num >= 1000) return num.toLocaleString('en-IN', { maximumFractionDigits: 0 });
    return num.toFixed(2);
}

function formatFailureReason(reason) {
    if (!reason) return '-';
    return reason.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getStatusBadge(status) {
    const badges = {
        'success': '<span class="badge badge-success">✓ Success</span>',
        'failed': '<span class="badge badge-failed">✗ Failed</span>',
        'recovered': '<span class="badge badge-recovered">↻ Recovered</span>',
        'pending': '<span class="badge badge-pending">⏳ Pending</span>',
    };
    return badges[status] || `<span class="badge">${status}</span>`;
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span> ${message}`;

    container.appendChild(toast);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
