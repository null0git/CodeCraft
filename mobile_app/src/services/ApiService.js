import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Toast from 'react-native-toast-message';

class ApiService {
  constructor() {
    this.baseURL = 'http://localhost:5000'; // Default server URL
    this.client = axios.create({
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      async (config) => {
        const token = await AsyncStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Use stored server URL if available
        const serverUrl = await AsyncStorage.getItem('server_url');
        if (serverUrl) {
          config.baseURL = serverUrl;
        } else {
          config.baseURL = this.baseURL;
        }
        
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.handleUnauthorized();
        }
        return Promise.reject(error);
      }
    );
  }

  async setServerUrl(url) {
    this.baseURL = url;
    await AsyncStorage.setItem('server_url', url);
  }

  async getServerUrl() {
    const stored = await AsyncStorage.getItem('server_url');
    return stored || this.baseURL;
  }

  handleUnauthorized() {
    AsyncStorage.removeItem('auth_token');
    Toast.show({
      type: 'error',
      text1: 'Authentication Error',
      text2: 'Please login again'
    });
  }

  // Authentication
  async login(username, password) {
    try {
      const response = await this.client.post('/auth/api/login', {
        username,
        password
      });
      
      if (response.data.token) {
        await AsyncStorage.setItem('auth_token', response.data.token);
        await AsyncStorage.setItem('user_info', JSON.stringify(response.data.user));
      }
      
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async logout() {
    try {
      await this.client.post('/auth/api/logout');
    } catch (error) {
      // Logout locally even if server request fails
    } finally {
      await AsyncStorage.removeItem('auth_token');
      await AsyncStorage.removeItem('user_info');
    }
  }

  // Dashboard Data
  async getDashboardData() {
    try {
      const response = await this.client.get('/api/dashboard/summary');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  // Cluster Management
  async getClusterInfo() {
    try {
      const response = await this.client.get('/cluster/api/info');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async getClusterMetrics() {
    try {
      const response = await this.client.get('/cluster/api/metrics');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async getClusterStatus() {
    try {
      const response = await this.client.get('/cluster/api/status');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async forceElection() {
    try {
      const response = await this.client.post('/cluster/api/force-election');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  // Node Management
  async getNodes() {
    try {
      const response = await this.client.get('/api/clients');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async getNodeDetail(nodeId) {
    try {
      const response = await this.client.get(`/api/clients/${nodeId}`);
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async executeTerminalCommand(nodeId, command) {
    try {
      const response = await this.client.post(`/terminal/api/execute`, {
        client_id: nodeId,
        command: command
      });
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  // Job Management
  async getJobs() {
    try {
      const response = await this.client.get('/api/jobs');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async getJobDetail(jobId) {
    try {
      const response = await this.client.get(`/api/jobs/${jobId}`);
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async getJobProgress(jobId) {
    try {
      const response = await this.client.get(`/api/jobs/${jobId}/progress`);
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async createJob(jobData) {
    try {
      const response = await this.client.post('/api/jobs', jobData);
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async stopJob(jobId) {
    try {
      const response = await this.client.post(`/api/jobs/${jobId}/stop`);
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async deleteJob(jobId) {
    try {
      const response = await this.client.delete(`/api/jobs/${jobId}`);
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  // System Health
  async ping() {
    try {
      const response = await this.client.get('/api/ping');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async getSystemHealth() {
    try {
      const response = await this.client.get('/api/system/health');
      return response.data;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  // Error handling
  handleApiError(error) {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.message || error.response.data?.error || 'Server error';
      return new Error(message);
    } else if (error.request) {
      // Network error
      return new Error('Network error - cannot reach server');
    } else {
      // Other error
      return new Error(error.message || 'Unknown error occurred');
    }
  }

  // WebSocket for real-time updates
  createWebSocket(path, onMessage, onError) {
    const wsUrl = this.baseURL.replace('http', 'ws') + path;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (onError) onError(error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };
    
    return ws;
  }
}

export default new ApiService();