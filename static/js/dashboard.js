// Dashboard real-time updates and charts
class DashboardManager {
    constructor() {
        this.charts = {};
        this.updateInterval = 30000; // 30 seconds
        this.isConnected = false;
        
        this.initializeCharts();
        this.setupWebSocketHandlers();
        this.startPeriodicUpdates();
    }
    
    initializeCharts() {
        // CPU Usage Chart
        const cpuCtx = document.getElementById('cpuChart');
        if (cpuCtx) {
            this.charts.cpu = new Chart(cpuCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU Usage %',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
        
        // RAM Usage Chart
        const ramCtx = document.getElementById('ramChart');
        if (ramCtx) {
            this.charts.ram = new Chart(ramCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Used', 'Free'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: [
                            'rgb(255, 99, 132)',
                            'rgb(201, 203, 207)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    }
    
    setupWebSocketHandlers() {
        // Handle client updates
        socket.on('client_update', (data) => {
            this.updateClientStats(data);
            this.updateConnectionStatus();
        });
        
        // Handle metrics updates
        socket.on('metrics_update', (data) => {
            this.updateServerMetrics(data.metrics);
        });
        
        // Handle job progress updates
        socket.on('job_progress_update', (data) => {
            this.updateJobProgress(data);
        });
        
        // Handle password cracked notifications
        socket.on('password_cracked', (data) => {
            this.showCrackNotification(data);
            this.updateCrackedStats();
        });
        
        // Handle job failures
        socket.on('job_failed', (data) => {
            this.showJobFailureNotification(data);
        });
        
        // Connection status
        socket.on('connect', () => {
            this.isConnected = true;
            this.updateConnectionIndicator(true);
        });
        
        socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionIndicator(false);
        });
    }
    
    updateClientStats(data) {
        const connectedElement = document.getElementById('connectedClients');
        if (connectedElement && data.status === 'connected') {
            const currentCount = parseInt(connectedElement.textContent);
            connectedElement.textContent = currentCount + 1;
        }
    }
    
    updateServerMetrics(metrics) {
        // Update CPU usage display
        const cpuElement = document.getElementById('serverCpuUsage');
        if (cpuElement && metrics.cpu_usage !== undefined) {
            const cpuUsage = Math.round(metrics.cpu_usage);
            cpuElement.style.width = cpuUsage + '%';
            cpuElement.textContent = cpuUsage + '%';
            
            // Update chart
            if (this.charts.cpu) {
                const now = new Date().toLocaleTimeString();
                const labels = this.charts.cpu.data.labels;
                const data = this.charts.cpu.data.datasets[0].data;
                
                labels.push(now);
                data.push(cpuUsage);
                
                // Keep only last 20 data points
                if (labels.length > 20) {
                    labels.shift();
                    data.shift();
                }
                
                this.charts.cpu.update('none');
            }
        }
        
        // Update RAM usage display
        const ramElement = document.getElementById('serverRamUsage');
        if (ramElement && metrics.ram_usage !== undefined) {
            const ramUsage = Math.round(metrics.ram_usage);
            ramElement.style.width = ramUsage + '%';
            ramElement.textContent = ramUsage + '%';
            
            // Update chart
            if (this.charts.ram) {
                this.charts.ram.data.datasets[0].data = [ramUsage, 100 - ramUsage];
                this.charts.ram.update('none');
            }
        }
        
        // Update disk usage display
        const diskElement = document.getElementById('serverDiskUsage');
        if (diskElement && metrics.disk_usage !== undefined) {
            const diskUsage = Math.round(metrics.disk_usage);
            diskElement.style.width = diskUsage + '%';
            diskElement.textContent = diskUsage + '%';
        }
    }
    
    updateJobProgress(data) {
        // Find job progress bars and update them
        const jobElements = document.querySelectorAll(`[data-job-id="${data.job_id}"]`);
        jobElements.forEach(element => {
            const progressBar = element.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = data.progress + '%';
                progressBar.textContent = data.progress.toFixed(1) + '%';
            }
        });
    }
    
    showCrackNotification(data) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'notification alert alert-success';
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i data-feather="key" class="me-2"></i>
                <div>
                    <strong>Password Cracked!</strong><br>
                    <small>${data.password} (Job: ${data.job_id})</small>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Replace feather icons
        feather.replace();
        
        // Show notification
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);
        
        // Hide notification after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 5000);
    }
    
    showJobFailureNotification(data) {
        const notification = document.createElement('div');
        notification.className = 'notification alert alert-danger';
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i data-feather="x-circle" class="me-2"></i>
                <div>
                    <strong>Job Failed!</strong><br>
                    <small>Job ${data.job_id}: ${data.error_message}</small>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        feather.replace();
        
        setTimeout(() => notification.classList.add('show'), 100);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 5000);
    }
    
    updateCrackedStats() {
        const crackedElement = document.getElementById('crackedToday');
        if (crackedElement) {
            const currentCount = parseInt(crackedElement.textContent);
            crackedElement.textContent = currentCount + 1;
        }
    }
    
    updateConnectionIndicator(connected) {
        const indicator = document.getElementById('connectionIndicator');
        if (indicator) {
            indicator.className = connected ? 
                'badge bg-success' : 'badge bg-danger';
            indicator.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }
    
    updateConnectionStatus() {
        // Update client counts
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (data.clients) {
                    const elements = {
                        'connectedClients': data.clients.connected,
                        'totalClients': data.clients.total,
                        'workingClients': data.clients.working,
                        'idleClients': data.clients.idle
                    };
                    
                    Object.entries(elements).forEach(([id, value]) => {
                        const element = document.getElementById(id);
                        if (element) {
                            element.textContent = value;
                        }
                    });
                }
                
                if (data.jobs) {
                    const runningJobsElement = document.getElementById('runningJobs');
                    if (runningJobsElement) {
                        runningJobsElement.textContent = data.jobs.running;
                    }
                }
            })
            .catch(error => console.error('Error updating stats:', error));
    }
    
    startPeriodicUpdates() {
        // Update server status every 30 seconds
        setInterval(() => {
            fetch('/dashboard/server_status')
                .then(response => response.json())
                .then(data => {
                    if (data.server_metrics) {
                        this.updateServerMetrics(data.server_metrics);
                    }
                    if (data.client_stats) {
                        // Update client statistics
                        Object.entries(data.client_stats).forEach(([key, value]) => {
                            const element = document.getElementById(key + 'Clients');
                            if (element) {
                                element.textContent = value;
                            }
                        });
                    }
                })
                .catch(error => console.error('Error fetching server status:', error));
        }, this.updateInterval);
        
        // Update recent activity every minute
        setInterval(() => {
            this.updateRecentActivity();
        }, 60000);
    }
    
    updateRecentActivity() {
        fetch('/api/recent_activity')
            .then(response => response.json())
            .then(data => {
                // Update recent jobs section if it exists
                const recentJobsContainer = document.getElementById('recentJobs');
                if (recentJobsContainer && data.recent_jobs) {
                    // Update recent jobs display
                    console.log('Recent activity updated:', data);
                }
            })
            .catch(error => console.error('Error fetching recent activity:', error));
    }
    
    refreshDashboard() {
        // Force refresh all dashboard data
        this.updateConnectionStatus();
        this.updateRecentActivity();
        
        // Fetch fresh server metrics
        fetch('/api/system_status')
            .then(response => response.json())
            .then(data => {
                if (data.server_metrics) {
                    this.updateServerMetrics(data.server_metrics);
                }
            })
            .catch(error => console.error('Error refreshing dashboard:', error));
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    const dashboard = new DashboardManager();
    
    // Add refresh button handler
    const refreshButton = document.getElementById('refreshDashboard');
    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            dashboard.refreshDashboard();
        });
    }
    
    // Make dashboard instance globally available
    window.dashboardManager = dashboard;
});

// Export for potential module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DashboardManager;
}
