Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.06)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.padding = 16;

const chartInstances = {};

function createChart(canvasId, config) {
    if (chartInstances[canvasId]) {
        chartInstances[canvasId].destroy();
    }
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    chartInstances[canvasId] = new Chart(ctx, config);
    return chartInstances[canvasId];
}

function renderDailyTrendChart(dailyData) {
    if (!dailyData || dailyData.length === 0) return;

    const labels = dailyData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
    });

    createChart('chart-daily-trend', {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Failed',
                    data: dailyData.map(d => d.failed || 0),
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ef4444',
                },
                {
                    label: 'Recovered',
                    data: dailyData.map(d => d.recovered || 0),
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#8b5cf6',
                },
                {
                    label: 'Successful',
                    data: dailyData.map(d => d.success || 0),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.05)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2,
                    pointHoverRadius: 5,
                    pointBackgroundColor: '#10b981',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    titleFont: { weight: '600' },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                },
                x: {
                    grid: { display: false },
                },
            },
        },
    });
}

function renderFailureReasonsChart(failureData) {
    if (!failureData || failureData.length === 0) return;

    const colors = [
        '#ef4444', '#f59e0b', '#8b5cf6', '#3b82f6',
        '#06b6d4', '#10b981', '#ec4899', '#f97316', '#6366f1',
    ];

    const labels = failureData.map(d =>
        d.failure_reason.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    );

    createChart('chart-failure-reasons', {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: failureData.map(d => d.count),
                backgroundColor: colors.slice(0, failureData.length),
                borderColor: 'rgba(10, 14, 26, 0.8)',
                borderWidth: 3,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: { font: { size: 11 }, padding: 12 },
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: (ctx) => {
                            const amount = failureData[ctx.dataIndex].total_amount;
                            return `${ctx.label}: ${ctx.parsed} txns (₹${formatAmount(amount)})`;
                        },
                    },
                },
            },
        },
    });
}

function renderBankChart(bankData) {
    if (!bankData || bankData.length === 0) return;

    const sorted = [...bankData].sort((a, b) => (b.failure_rate || 0) - (a.failure_rate || 0)).slice(0, 8);

    createChart('chart-banks', {
        type: 'bar',
        data: {
            labels: sorted.map(d => d.bank_name),
            datasets: [
                {
                    label: 'Failure Rate (%)',
                    data: sorted.map(d => d.failure_rate || 0),
                    backgroundColor: sorted.map(d =>
                        (d.failure_rate || 0) > 35 ? 'rgba(239, 68, 68, 0.7)' :
                        (d.failure_rate || 0) > 25 ? 'rgba(245, 158, 11, 0.7)' :
                        'rgba(59, 130, 246, 0.7)'
                    ),
                    borderColor: sorted.map(d =>
                        (d.failure_rate || 0) > 35 ? '#ef4444' :
                        (d.failure_rate || 0) > 25 ? '#f59e0b' :
                        '#3b82f6'
                    ),
                    borderWidth: 1,
                    borderRadius: 6,
                    barThickness: 24,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: (ctx) => {
                            const bank = sorted[ctx.dataIndex];
                            return `Failure Rate: ${ctx.parsed.x}% (${bank.failed} of ${bank.total} txns)`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: { callback: v => v + '%' },
                },
                y: {
                    grid: { display: false },
                },
            },
        },
    });
}

function renderHourlyChart(hourlyData) {
    if (!hourlyData || hourlyData.length === 0) return;

    const fullData = Array.from({ length: 24 }, (_, i) => {
        const found = hourlyData.find(d => d.hour === i);
        return {
            hour: i,
            total: found ? found.total : 0,
            failed: found ? found.failed : 0,
            recovered: found ? found.recovered : 0,
        };
    });

    const labels = fullData.map(d => {
        const h = d.hour;
        return h === 0 ? '12 AM' : h < 12 ? `${h} AM` : h === 12 ? '12 PM' : `${h - 12} PM`;
    });

    createChart('chart-hourly', {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Failed',
                    data: fullData.map(d => d.failed),
                    backgroundColor: 'rgba(239, 68, 68, 0.6)',
                    borderRadius: 4,
                    barPercentage: 0.7,
                },
                {
                    label: 'Recovered',
                    data: fullData.map(d => d.recovered),
                    backgroundColor: 'rgba(139, 92, 246, 0.6)',
                    borderRadius: 4,
                    barPercentage: 0.7,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 10 }, maxRotation: 45 },
                },
                y: {
                    beginAtZero: true,
                    stacked: true,
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                },
            },
        },
    });
}

function renderFeatureImportanceChart(modelInfo) {
    if (!modelInfo || !modelInfo.top_features) return;

    const features = Object.entries(modelInfo.top_features)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    const labels = features.map(([name]) =>
        name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    );

    createChart('chart-feature-importance', {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Importance Score',
                data: features.map(([, val]) => (val * 100).toFixed(2)),
                backgroundColor: features.map((_, i) => {
                    const gradient = [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(99, 102, 241, 0.7)',
                        'rgba(139, 92, 246, 0.6)',
                        'rgba(168, 85, 247, 0.5)',
                        'rgba(192, 132, 252, 0.4)',
                    ];
                    return gradient[Math.min(i, gradient.length - 1)] || 'rgba(148, 163, 184, 0.3)';
                }),
                borderRadius: 6,
                barThickness: 22,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    callbacks: {
                        label: (ctx) => `Importance: ${ctx.parsed.x}%`,
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: { callback: v => v + '%' },
                },
                y: {
                    grid: { display: false },
                    ticks: { font: { size: 11 } },
                },
            },
        },
    });
}

function formatAmount(amount) {
    if (!amount) return '0';
    if (amount >= 10000000) return (amount / 10000000).toFixed(2) + ' Cr';
    if (amount >= 100000) return (amount / 100000).toFixed(2) + ' L';
    if (amount >= 1000) return (amount / 1000).toFixed(1) + 'K';
    return amount.toFixed(0);
}
