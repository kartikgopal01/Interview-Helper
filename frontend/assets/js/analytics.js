document.addEventListener('DOMContentLoaded', function() {
    loadAnalytics();
});

function loadAnalytics() {
    fetch('/practice-analytics')
        .then(response => response.json())
        .then(data => {
            updateOverallStats(data);
            updateScoreDistribution(data);
            updateRolePerformance(data);
            updateRecentActivity(data);
        });
}

function updateOverallStats(data) {
    const statsDiv = document.getElementById('overallStats');
    statsDiv.innerHTML = `
        <div class="bg-gray-800 p-4 rounded-lg">
            <p class="text-blue-400 font-bold">Total Practices: 
                <span class="text-gray-300">${data.total_practices}</span>
            </p>
            <p class="text-blue-400 font-bold">Average Score: 
                <span class="text-gray-300">${data.average_score.toFixed(2)}</span>
            </p>
        </div>
    `;
}

function updateScoreDistribution(data) {
    const ctx = document.getElementById('scoreDistributionChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: Object.keys(data.by_role),
            datasets: [{
                label: 'Score Distribution',
                data: Object.values(data.by_role).map(role => role.average_score),
                borderColor: 'rgba(96, 165, 250, 1)',
                backgroundColor: 'rgba(96, 165, 250, 0.2)',
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: '#9CA3AF' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(75, 85, 99, 0.2)' },
                    ticks: { color: '#9CA3AF' }
                },
                x: {
                    grid: { color: 'rgba(75, 85, 99, 0.2)' },
                    ticks: { color: '#9CA3AF' }
                }
            }
        }
    });
}

function updateRolePerformance(data) {
    const ctx = document.getElementById('rolePerformanceChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(data.by_role),
            datasets: [{
                label: 'Average Score by Role',
                data: Object.values(data.by_role).map(role => role.average_score),
                backgroundColor: 'rgba(96, 165, 250, 0.5)',
                borderColor: 'rgba(96, 165, 250, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: '#9CA3AF' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(75, 85, 99, 0.2)' },
                    ticks: { color: '#9CA3AF' }
                },
                x: {
                    grid: { color: 'rgba(75, 85, 99, 0.2)' },
                    ticks: { color: '#9CA3AF' }
                }
            }
        }
    });
}

function updateRecentActivity(data) {
    // This would require additional endpoint to get recent activity
    const activityDiv = document.getElementById('recentActivity');
    activityDiv.innerHTML = `
        <div class="text-gray-300">
            <p class="italic">Recent activity data will be shown here...</p>
        </div>
    `;
} 