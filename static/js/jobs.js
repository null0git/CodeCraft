// Job management functionality
class JobManager {
    constructor() {
        this.jobs = new Map();
        this.updateInterval = 15000; // 15 seconds
        this.selectedJob = null;
        
        this.setupEventHandlers();
        this.setupWebSocketHandlers();
        this.startPeriodicUpdates();
    }
    
    setupEventHandlers() {
        // Filter buttons
        const filterButtons = document.querySelectorAll('[data-filter]');
        filterButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.filterJobs(e.target.dataset.filter);
                
                // Update active button
                filterButtons.forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
            });
        });
        
        // Refresh button
        const refreshButton = document.getElementById('refreshJobs');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => this.refreshJobList());
        }
        
        // Sort handlers
        const sortSelect = document.getElementById('sortJobs');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.sortJobs(e.target.value);
            });
        }
    }
    
    setupWebSocketHandlers() {
        // Handle job progress updates
        socket.on('job_progress_update', (data) => {
            this.updateJobProgress(data);
        });
        
        // Handle password cracked notifications
        socket.on('password_cracked', (data) => {
            this.handlePasswordCracked(data);
        });
        
        // Handle job completion
        socket.on('job_completed', (data) => {
            this.handleJobCompleted(data);
        });
        
        // Handle job failures
        socket.on('job_failed', (data) => {
            this.handleJobFailed(data);
        });
        
        // Handle job assignments
        socket.on('job_assigned', (data) => {
            this.handleJobAssigned(data);
        });
    }
    
    updateJobProgress(data) {
        const jobRow = document.querySelector(`tr[data-job-id="${data.job_id}"]`);
        if (jobRow) {
            // Update progress bar
            const progressBar = jobRow.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = data.progress + '%';
                progressBar.textContent = data.progress.toFixed(1) + '%';
                
                // Update progress bar color based on progress
                progressBar.className = 'progress-bar';
                if (data.progress >= 100) {
                    progressBar.classList.add('bg-success');
                } else if (data.progress >= 75) {
                    progressBar.classList.add('bg-info');
                } else if (data.progress >= 50) {
                    progressBar.classList.add('bg-warning');
                } else {
                    progressBar.classList.add('bg-primary');
                }
            }
            
            // Update ETA if provided
            if (data.estimated_time) {
                const etaElement = jobRow.querySelector('.eta-display');
                if (etaElement) {
                    const minutes = Math.floor(data.estimated_time / 60);
                    const seconds = data.estimated_time % 60;
                    etaElement.textContent = `ETA: ${minutes}m ${seconds}s`;
                }
            }
        }
        
        // Update job counts
        this.updateJobCounts();
    }
    
    handlePasswordCracked(data) {
        const jobRow = document.querySelector(`tr[data-job-id="${data.job_id}"]`);
        if (jobRow) {
            // Update cracked count in the hash display
            const hashInfo = jobRow.querySelector('.hash-info');
            if (hashInfo) {
                const text = hashInfo.textContent;
                const match = text.match(/(\d+) hashes.*\((\d+) cracked\)/);
                if (match) {
                    const totalHashes = parseInt(match[1]);
                    const crackedHashes = parseInt(match[2]) + 1;
                    hashInfo.innerHTML = `${totalHashes} hashes<br><small class="text-muted">(${crackedHashes} cracked)</small>`;
                }
            }
        }
        
        // Show notification
        this.showCrackNotification(data);
    }
    
    handleJobCompleted(data) {
        const jobRow = document.querySelector(`tr[data-job-id="${data.job_id}"]`);
        if (jobRow) {
            // Update status badge
            const statusBadge = jobRow.querySelector('.badge');
            if (statusBadge) {
                statusBadge.className = 'badge bg-success';
                statusBadge.innerHTML = '<i data-feather="check-circle" width="12" height="12"></i> Completed';
                feather.replace();
            }
            
            // Update progress bar to 100%
            const progressBar = jobRow.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                progressBar.className = 'progress-bar bg-success';
            }
            
            // Update action buttons
            const actionButtons = jobRow.querySelector('.btn-group-vertical');
            if (actionButtons) {
                actionButtons.innerHTML = `
                    <a href="/jobs/view/${data.job_id}" class="btn btn-outline-primary btn-sm">
                        <i data-feather="eye"></i> View
                    </a>
                    <a href="/jobs/download_results/${data.job_id}" class="btn btn-outline-success btn-sm">
                        <i data-feather="download"></i> Results
                    </a>
                `;
                feather.replace();
            }
        }
        
        this.updateJobCounts();
    }
    
    handleJobFailed(data) {
        const jobRow = document.querySelector(`tr[data-job-id="${data.job_id}"]`);
        if (jobRow) {
            // Update status badge
            const statusBadge = jobRow.querySelector('.badge');
            if (statusBadge) {
                statusBadge.className = 'badge bg-danger';
                statusBadge.innerHTML = '<i data-feather="x-circle" width="12" height="12"></i> Failed';
                feather.replace();
            }
            
            // Update progress bar
            const progressBar = jobRow.querySelector('.progress-bar');
            if (progressBar) {
                progressBar.className = 'progress-bar bg-danger';
            }
        }
        
        // Show error notification
        this.showJobFailureNotification(data);
        this.updateJobCounts();
    }
    
    handleJobAssigned(data) {
        const jobRow = document.querySelector(`tr[data-job-id="${data.job_id}"]`);
        if (jobRow) {
            // Update status to running
            const statusBadge = jobRow.querySelector('.badge');
            if (statusBadge) {
                statusBadge.className = 'badge bg-warning';
                statusBadge.innerHTML = '<i data-feather="play-circle" width="12" height="12"></i> Running';
                feather.replace();
            }
            
            // Update client assignment
            const clientInfo = jobRow.querySelector('.client-info');
            if (clientInfo && data.client_hostname) {
                clientInfo.innerHTML = `<strong>${data.client_hostname}</strong><br><small class="text-muted">${data.client_id}</small>`;
            }
        }
        
        this.updateJobCounts();
    }
    
    showCrackNotification(data) {
        const notification = document.createElement('div');
        notification.className = 'notification alert alert-success';
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i data-feather="key" class="me-2"></i>
                <div>
                    <strong>Password Cracked!</strong><br>
                    <small>Job ${data.job_id}: ${data.hash_value.substring(0, 16)}... → ${data.password}</small>
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
    
    filterJobs(filter) {
        const rows = document.querySelectorAll('tbody tr[data-status]');
        
        rows.forEach(row => {
            const status = row.dataset.status;
            let show = true;
            
            if (filter !== 'all') {
                show = status === filter;
            }
            
            row.style.display = show ? '' : 'none';
        });
    }
    
    sortJobs(sortBy) {
        const tbody = document.querySelector('tbody');
        if (!tbody) return;
        
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            let aValue, bValue;
            
            switch (sortBy) {
                case 'name':
                    aValue = a.querySelector('strong').textContent;
                    bValue = b.querySelector('strong').textContent;
                    return aValue.localeCompare(bValue);
                    
                case 'status':
                    aValue = a.dataset.status;
                    bValue = b.dataset.status;
                    return aValue.localeCompare(bValue);
                    
                case 'progress':
                    aValue = parseFloat(a.querySelector('.progress-bar').textContent);
                    bValue = parseFloat(b.querySelector('.progress-bar').textContent);
                    return bValue - aValue; // Descending
                    
                case 'created':
                default:
                    // Sort by creation date (newest first)
                    const aDate = new Date(a.querySelector('td:nth-last-child(2)').textContent);
                    const bDate = new Date(b.querySelector('td:nth-last-child(2)').textContent);
                    return bDate - aDate;
            }
        });
        
        // Clear and re-append sorted rows
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));
    }
    
    updateJobCounts() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (data.jobs) {
                    const elements = {
                        'pendingCount': data.jobs.pending,
                        'runningCount': data.jobs.running,
                        'completedCount': data.jobs.completed,
                        'failedCount': data.jobs.failed
                    };
                    
                    Object.entries(elements).forEach(([id, value]) => {
                        const element = document.getElementById(id);
                        if (element) {
                            element.textContent = value;
                        }
                    });
                }
            })
            .catch(error => console.error('Error updating job counts:', error));
    }
    
    refreshJobList() {
        fetch('/api/jobs')
            .then(response => response.json())
            .then(jobs => {
                this.updateJobTable(jobs);
                this.updateJobCounts();
            })
            .catch(error => console.error('Error refreshing job list:', error));
    }
    
    updateJobTable(jobs) {
        const tbody = document.querySelector('tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        jobs.forEach(job => {
            const row = this.createJobRow(job);
            tbody.appendChild(row);
        });
        
        feather.replace();
    }
    
    createJobRow(job) {
        const row = document.createElement('tr');
        row.dataset.status = job.status;
        row.dataset.jobId = job.id;
        
        let statusBadge = '';
        let progressClass = 'bg-secondary';
        
        switch (job.status) {
            case 'pending':
                statusBadge = '<span class="badge bg-secondary"><i data-feather="clock" width="12" height="12"></i> Pending</span>';
                break;
            case 'running':
                statusBadge = '<span class="badge bg-warning"><i data-feather="play-circle" width="12" height="12"></i> Running</span>';
                progressClass = 'bg-warning';
                break;
            case 'completed':
                statusBadge = '<span class="badge bg-success"><i data-feather="check-circle" width="12" height="12"></i> Completed</span>';
                progressClass = 'bg-success';
                break;
            case 'failed':
                statusBadge = '<span class="badge bg-danger"><i data-feather="x-circle" width="12" height="12"></i> Failed</span>';
                progressClass = 'bg-danger';
                break;
            default:
                statusBadge = `<span class="badge bg-secondary">${job.status}</span>`;
        }
        
        const actionButtons = job.status === 'completed' ? `
            <a href="/jobs/view/${job.id}" class="btn btn-outline-primary btn-sm">
                <i data-feather="eye"></i> View
            </a>
            <a href="/jobs/download_results/${job.id}" class="btn btn-outline-success btn-sm">
                <i data-feather="download"></i> Results
            </a>
        ` : `
            <a href="/jobs/view/${job.id}" class="btn btn-outline-primary btn-sm">
                <i data-feather="eye"></i> View
            </a>
            ${job.status === 'running' || job.status === 'pending' ? `
                <button class="btn btn-outline-warning btn-sm" onclick="cancelJob(${job.id})">
                    <i data-feather="stop-circle"></i> Cancel
                </button>
            ` : ''}
        `;
        
        row.innerHTML = `
            <td>
                <strong>${job.name}</strong>
                <br>
                <small class="text-muted hash-info">
                    ${job.total_hashes} hashes
                    ${job.cracked_hashes > 0 ? `(${job.cracked_hashes} cracked)` : ''}
                </small>
            </td>
            <td>
                <span class="badge bg-secondary">${job.hash_type}</span>
                <br>
                <small class="text-muted">${job.attack_mode || 'dictionary'}</small>
            </td>
            <td>${statusBadge}</td>
            <td>
                <div class="progress mb-1" style="height: 20px;">
                    <div class="progress-bar ${progressClass}" role="progressbar" 
                         style="width: ${job.progress_percent}%"
                         aria-valuenow="${job.progress_percent}" 
                         aria-valuemin="0" aria-valuemax="100">
                        ${job.progress_percent.toFixed(1)}%
                    </div>
                </div>
                ${job.estimated_time && job.status === 'running' ? `
                    <small class="text-muted eta-display">
                        ETA: ${Math.floor(job.estimated_time / 60)}m ${job.estimated_time % 60}s
                    </small>
                ` : ''}
            </td>
            <td class="client-info">
                ${job.client_id ? `
                    <strong>Client</strong>
                    <br>
                    <small class="text-muted">${job.client_id}</small>
                ` : '<span class="text-muted">Unassigned</span>'}
            </td>
            <td>
                ${new Date(job.created_at).toLocaleDateString()}
                <br>
                <small class="text-muted">by User</small>
            </td>
            <td>
                <div class="btn-group-vertical btn-group-sm">
                    ${actionButtons}
                </div>
            </td>
        `;
        
        return row;
    }
    
    startPeriodicUpdates() {
        setInterval(() => {
            this.updateJobCounts();
            
            // Update progress for running jobs
            const runningJobRows = document.querySelectorAll('tr[data-status="running"]');
            runningJobRows.forEach(row => {
                const jobId = row.dataset.jobId;
                if (jobId) {
                    fetch(`/api/job/${jobId}/progress`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.job) {
                                this.updateJobProgress({
                                    job_id: parseInt(jobId),
                                    progress: data.job.progress_percent,
                                    estimated_time: data.job.estimated_time
                                });
                            }
                        })
                        .catch(error => console.error('Error fetching job progress:', error));
                }
            });
        }, this.updateInterval);
    }
}

// Global function for canceling jobs
function cancelJob(jobId) {
    if (confirm('Are you sure you want to cancel this job?')) {
        fetch(`/jobs/cancel/${jobId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error cancelling job: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error cancelling job:', error);
            alert('Failed to cancel job');
        });
    }
}

// Initialize job manager when page loads
document.addEventListener('DOMContentLoaded', function() {
    const jobManager = new JobManager();
    window.jobManager = jobManager;
});
