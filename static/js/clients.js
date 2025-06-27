// Client management functionality
class ClientManager {
    constructor() {
        this.clients = new Map();
        this.updateInterval = 10000; // 10 seconds
        this.selectedClient = null;
        
        this.setupEventHandlers();
        this.setupWebSocketHandlers();
        this.startPeriodicUpdates();
    }
    
    setupEventHandlers() {
        // Network scan button
        const scanButton = document.getElementById('scanNetwork');
        if (scanButton) {
            scanButton.addEventListener('click', () => this.scanNetwork());
        }
        
        const scanEmptyButton = document.getElementById('scanNetworkEmpty');
        if (scanEmptyButton) {
            scanEmptyButton.addEventListener('click', () => this.scanNetwork());
        }
        
        // Filter buttons
        const filterButtons = document.querySelectorAll('[data-filter]');
        filterButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.filterClients(e.target.dataset.filter);
                
                // Update active button
                filterButtons.forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
            });
        });
        
        // Refresh button
        const refreshButton = document.getElementById('refreshClients');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => this.refreshClientList());
        }
    }
    
    setupWebSocketHandlers() {
        // Handle client registration
        socket.on('client_update', (data) => {
            this.updateClientStatus(data);
        });
        
        // Handle client metrics updates
        socket.on('metrics_update', (data) => {
            this.updateClientMetrics(data);
        });
        
        // Handle client disconnections
        socket.on('client_disconnect', (data) => {
            this.handleClientDisconnect(data);
        });
        
        // Connection status
        socket.on('connect', () => {
            console.log('Connected to server');
        });
        
        socket.on('disconnect', () => {
            console.log('Disconnected from server');
        });
    }
    
    updateClientStatus(data) {
        const clientRow = document.querySelector(`tr[data-client-id="${data.client_id}"]`);
        if (clientRow) {
            // Update status badge
            const statusBadge = clientRow.querySelector('.badge');
            if (statusBadge) {
                statusBadge.className = 'badge';
                if (data.status === 'connected') {
                    statusBadge.classList.add('bg-success');
                    statusBadge.innerHTML = '<i data-feather="check-circle" width="12" height="12"></i> Connected';
                } else if (data.status === 'working') {
                    statusBadge.classList.add('bg-warning');
                    statusBadge.innerHTML = '<i data-feather="cpu" width="12" height="12"></i> Working';
                } else {
                    statusBadge.classList.add('bg-danger');
                    statusBadge.innerHTML = '<i data-feather="x-circle" width="12" height="12"></i> Disconnected';
                }
                
                feather.replace();
            }
            
            // Update system info if provided
            if (data.system_info) {
                this.updateClientSystemInfo(clientRow, data.system_info);
            }
        } else if (data.status === 'connected') {
            // New client, refresh the entire list
            this.refreshClientList();
        }
        
        this.updateClientCounts();
    }
    
    updateClientMetrics(data) {
        const clientRow = document.querySelector(`tr[data-client-id="${data.client_id}"]`);
        if (clientRow && data.metrics) {
            // Update CPU usage
            const cpuProgress = clientRow.querySelector('.progress .progress-bar');
            if (cpuProgress) {
                cpuProgress.style.width = data.metrics.cpu_usage + '%';
            }
            
            // Update RAM usage
            const ramProgress = clientRow.querySelectorAll('.progress .progress-bar')[1];
            if (ramProgress) {
                ramProgress.style.width = data.metrics.ram_usage + '%';
            }
            
            // Update disk usage
            const diskProgress = clientRow.querySelectorAll('.progress .progress-bar')[2];
            if (diskProgress) {
                diskProgress.style.width = data.metrics.disk_usage + '%';
            }
            
            // Update latency
            const latencyElement = clientRow.querySelector('.text-center strong');
            if (latencyElement && data.metrics.network_latency !== undefined) {
                latencyElement.textContent = Math.round(data.metrics.network_latency) + 'ms';
            }
        }
    }
    
    updateClientSystemInfo(clientRow, systemInfo) {
        // Update hostname
        const hostnameElement = clientRow.querySelector('strong');
        if (hostnameElement && systemInfo.hostname) {
            hostnameElement.textContent = systemInfo.hostname;
        }
        
        // Update CPU info
        const cpuModelElement = clientRow.querySelector('td:nth-child(4) strong');
        if (cpuModelElement && systemInfo.cpu_model) {
            cpuModelElement.textContent = systemInfo.cpu_model;
        }
    }
    
    handleClientDisconnect(data) {
        const clientRow = document.querySelector(`tr[data-client-id="${data.client_id}"]`);
        if (clientRow) {
            // Update status to disconnected
            const statusBadge = clientRow.querySelector('.badge');
            if (statusBadge) {
                statusBadge.className = 'badge bg-danger';
                statusBadge.innerHTML = '<i data-feather="x-circle" width="12" height="12"></i> Disconnected';
                feather.replace();
            }
        }
        
        this.updateClientCounts();
    }
    
    updateClientCounts() {
        fetch('/api/clients')
            .then(response => response.json())
            .then(clients => {
                const counts = {
                    connected: 0,
                    working: 0,
                    disconnected: 0
                };
                
                clients.forEach(client => {
                    if (client.status === 'connected') counts.connected++;
                    else if (client.status === 'working') counts.working++;
                    else counts.disconnected++;
                });
                
                counts.idle = counts.connected - counts.working;
                
                // Update count displays
                const elements = {
                    'connectedCount': counts.connected,
                    'workingCount': counts.working,
                    'idleCount': counts.idle,
                    'disconnectedCount': counts.disconnected
                };
                
                Object.entries(elements).forEach(([id, value]) => {
                    const element = document.getElementById(id);
                    if (element) {
                        element.textContent = value;
                    }
                });
            })
            .catch(error => console.error('Error updating client counts:', error));
    }
    
    scanNetwork() {
        const scanButton = document.getElementById('scanNetwork') || document.getElementById('scanNetworkEmpty');
        if (scanButton) {
            const originalText = scanButton.innerHTML;
            scanButton.innerHTML = '<i data-feather="loader" class="icon-spin"></i> Scanning...';
            scanButton.disabled = true;
            feather.replace();
        }
        
        fetch('/clients/scan_network', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Scan failed: ' + data.error);
            } else {
                console.log(`Network scan completed. Found ${data.active_hosts} hosts.`);
                // Optionally refresh client list
                this.refreshClientList();
            }
        })
        .catch(error => {
            console.error('Error scanning network:', error);
            alert('Network scan failed: ' + error);
        })
        .finally(() => {
            if (scanButton) {
                scanButton.innerHTML = '<i data-feather="search"></i> Scan Network';
                scanButton.disabled = false;
                feather.replace();
            }
        });
    }
    
    filterClients(filter) {
        const rows = document.querySelectorAll('#clientsTableBody tr');
        
        rows.forEach(row => {
            const statusBadge = row.querySelector('.badge');
            let show = true;
            
            if (filter !== 'all' && statusBadge) {
                const status = statusBadge.textContent.toLowerCase().trim();
                show = status.includes(filter);
            }
            
            row.style.display = show ? '' : 'none';
        });
    }
    
    refreshClientList() {
        fetch('/api/clients')
            .then(response => response.json())
            .then(clients => {
                this.updateClientTable(clients);
                this.updateClientCounts();
            })
            .catch(error => console.error('Error refreshing client list:', error));
    }
    
    updateClientTable(clients) {
        const tbody = document.getElementById('clientsTableBody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        clients.forEach(client => {
            const row = this.createClientRow(client);
            tbody.appendChild(row);
        });
        
        feather.replace();
    }
    
    createClientRow(client) {
        const row = document.createElement('tr');
        row.dataset.clientId = client.client_id;
        
        let statusBadge = '';
        if (client.status === 'connected') {
            statusBadge = '<span class="badge bg-success"><i data-feather="check-circle" width="12" height="12"></i> Connected</span>';
        } else if (client.status === 'working') {
            statusBadge = '<span class="badge bg-warning"><i data-feather="cpu" width="12" height="12"></i> Working</span>';
        } else {
            statusBadge = '<span class="badge bg-danger"><i data-feather="x-circle" width="12" height="12"></i> Disconnected</span>';
        }
        
        row.innerHTML = `
            <td>${statusBadge}</td>
            <td>
                <strong>${client.hostname || 'Unknown'}</strong>
                <br>
                <small class="text-muted">${client.client_id}</small>
            </td>
            <td>
                ${client.ip_address}
                <br>
                <small class="text-muted">${client.mac_address || 'Unknown'}</small>
            </td>
            <td>
                <div>
                    <strong>CPU Model</strong>
                    <br>
                    <small class="text-muted">Cores: N/A | Freq: N/A MHz</small>
                    <br>
                    <small class="text-muted">OS Info</small>
                </div>
            </td>
            <td>
                <div class="mb-1">
                    <small>CPU: ${(client.cpu_usage || 0).toFixed(1)}%</small>
                    <div class="progress progress-sm">
                        <div class="progress-bar" style="width: ${client.cpu_usage || 0}%"></div>
                    </div>
                </div>
                <div class="mb-1">
                    <small>RAM: ${(client.ram_usage || 0).toFixed(1)}%</small>
                    <div class="progress progress-sm">
                        <div class="progress-bar bg-info" style="width: ${client.ram_usage || 0}%"></div>
                    </div>
                </div>
                <div>
                    <small>Disk: ${(client.disk_usage || 0).toFixed(1)}%</small>
                    <div class="progress progress-sm">
                        <div class="progress-bar bg-warning" style="width: ${client.disk_usage || 0}%"></div>
                    </div>
                </div>
            </td>
            <td>
                <div class="text-center">
                    <div class="mb-1">
                        <small>Latency</small>
                        <br>
                        <strong>${Math.round(client.network_latency || 0)}ms</strong>
                    </div>
                    <div>
                        <small>Last Seen</small>
                        <br>
                        <small class="text-muted">
                            ${client.last_seen ? new Date(client.last_seen).toLocaleTimeString() : 'Never'}
                        </small>
                    </div>
                </div>
            </td>
            <td>
                <div class="btn-group-vertical btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="openTerminal('${client.client_id}')">
                        <i data-feather="terminal"></i> Terminal
                    </button>
                    <button class="btn btn-outline-info" onclick="viewClientDetails('${client.client_id}')">
                        <i data-feather="info"></i> Details
                    </button>
                    ${client.status === 'working' ? 
                        `<button class="btn btn-outline-warning" onclick="stopClient('${client.client_id}')">
                            <i data-feather="stop-circle"></i> Stop
                        </button>` : ''
                    }
                </div>
            </td>
        `;
        
        return row;
    }
    
    startPeriodicUpdates() {
        setInterval(() => {
            this.updateClientCounts();
        }, this.updateInterval);
    }
}

// Global functions for button actions
function openTerminal(clientId) {
    const modal = new bootstrap.Modal(document.getElementById('terminalModal'));
    modal.show();
    
    // In a real implementation, this would set up a WebSocket connection
    // to provide actual terminal access using xterm.js
    console.log(`Opening terminal for client: ${clientId}`);
}

function viewClientDetails(clientId) {
    fetch(`/clients/client/${clientId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error loading client details: ' + data.error);
                return;
            }
            
            const modalBody = document.getElementById('clientDetailsBody');
            const client = data.client;
            
            modalBody.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <h6>System Information</h6>
                        <table class="table table-sm">
                            <tr>
                                <td><strong>Hostname:</strong></td>
                                <td>${client.hostname || 'Unknown'}</td>
                            </tr>
                            <tr>
                                <td><strong>IP Address:</strong></td>
                                <td>${client.ip_address}</td>
                            </tr>
                            <tr>
                                <td><strong>MAC Address:</strong></td>
                                <td>${client.mac_address || 'Unknown'}</td>
                            </tr>
                            <tr>
                                <td><strong>OS:</strong></td>
                                <td>${client.os_info || 'Unknown'}</td>
                            </tr>
                            <tr>
                                <td><strong>CPU:</strong></td>
                                <td>${client.cpu_model || 'Unknown'}</td>
                            </tr>
                            <tr>
                                <td><strong>Cores:</strong></td>
                                <td>${client.cpu_cores || 'Unknown'}</td>
                            </tr>
                            <tr>
                                <td><strong>RAM Total:</strong></td>
                                <td>${client.ram_total ? (client.ram_total / 1024 / 1024 / 1024).toFixed(2) + ' GB' : 'Unknown'}</td>
                            </tr>
                        </table>
                    </div>
                    <div class="col-md-6">
                        <h6>Current Metrics</h6>
                        <table class="table table-sm">
                            <tr>
                                <td><strong>CPU Usage:</strong></td>
                                <td>${(client.cpu_usage || 0).toFixed(1)}%</td>
                            </tr>
                            <tr>
                                <td><strong>RAM Usage:</strong></td>
                                <td>${(client.ram_usage || 0).toFixed(1)}%</td>
                            </tr>
                            <tr>
                                <td><strong>Disk Usage:</strong></td>
                                <td>${(client.disk_usage || 0).toFixed(1)}%</td>
                            </tr>
                            <tr>
                                <td><strong>Network Latency:</strong></td>
                                <td>${Math.round(client.network_latency || 0)}ms</td>
                            </tr>
                            <tr>
                                <td><strong>Status:</strong></td>
                                <td>${client.status}</td>
                            </tr>
                            <tr>
                                <td><strong>Last Seen:</strong></td>
                                <td>${client.last_seen ? new Date(client.last_seen).toLocaleString() : 'Never'}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                
                ${data.jobs && data.jobs.length > 0 ? `
                <hr>
                <h6>Recent Jobs</h6>
                <div class="table-responsive">
                    <table class="table table-sm table-striped">
                        <thead>
                            <tr>
                                <th>Job Name</th>
                                <th>Status</th>
                                <th>Progress</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.jobs.map(job => `
                                <tr>
                                    <td>${job.name}</td>
                                    <td><span class="badge bg-secondary">${job.status}</span></td>
                                    <td>${job.progress_percent.toFixed(1)}%</td>
                                    <td>${new Date(job.created_at).toLocaleString()}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                ` : '<hr><p class="text-muted">No recent jobs for this client.</p>'}
            `;
            
            const modal = new bootstrap.Modal(document.getElementById('clientDetailsModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading client details:', error);
            alert('Failed to load client details');
        });
}

function stopClient(clientId) {
    if (confirm('Are you sure you want to stop the current job on this client?')) {
        fetch(`/clients/client/${clientId}/stop`, {
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
                alert('Error stopping client: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error stopping client:', error);
            alert('Failed to stop client');
        });
    }
}

// Initialize client manager when page loads
document.addEventListener('DOMContentLoaded', function() {
    const clientManager = new ClientManager();
    window.clientManager = clientManager;
});
