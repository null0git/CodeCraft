// Utility functions for formatting and data manipulation

export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

export const formatDuration = (seconds) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
};

export const getStatusColor = (status) => {
  const colors = {
    online: '#E8F5E8',
    working: '#E3F2FD',
    offline: '#FFEBEE',
    idle: '#FFF3E0',
    failed: '#FFEBEE',
    completed: '#E8F5E8',
    running: '#E3F2FD',
    pending: '#FFF3E0',
    stopped: '#F3E5F5',
    error: '#FFEBEE',
    healthy: '#E8F5E8',
    degraded: '#FFF3E0',
    critical: '#FFEBEE',
  };
  
  return colors[status?.toLowerCase()] || '#F5F5F5';
};

export const getStatusTextColor = (status) => {
  const colors = {
    online: '#2E7D32',
    working: '#1976D2',
    offline: '#D32F2F',
    idle: '#F57C00',
    failed: '#D32F2F',
    completed: '#2E7D32',
    running: '#1976D2',
    pending: '#F57C00',
    stopped: '#7B1FA2',
    error: '#D32F2F',
    healthy: '#2E7D32',
    degraded: '#F57C00',
    critical: '#D32F2F',
  };
  
  return colors[status?.toLowerCase()] || '#666666';
};

export const formatPercentage = (value, decimals = 1) => {
  return `${parseFloat(value).toFixed(decimals)}%`;
};

export const formatNumber = (number, decimals = 0) => {
  if (number >= 1000000) {
    return (number / 1000000).toFixed(decimals) + 'M';
  } else if (number >= 1000) {
    return (number / 1000).toFixed(decimals) + 'K';
  }
  return number.toString();
};

export const formatCurrency = (amount, currency = 'USD') => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(amount);
};

export const formatDate = (date, options = {}) => {
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  };
  
  return new Date(date).toLocaleDateString('en-US', { ...defaultOptions, ...options });
};

export const formatRelativeTime = (date) => {
  const now = new Date();
  const diffInSeconds = Math.floor((now - new Date(date)) / 1000);
  
  if (diffInSeconds < 60) {
    return 'Just now';
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
  } else {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days} day${days !== 1 ? 's' : ''} ago`;
  }
};

export const calculateProgress = (current, total) => {
  if (total === 0) return 0;
  return Math.min((current / total) * 100, 100);
};

export const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validateUrl = (url) => {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
};

export const generateColor = (str) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  const hue = hash % 360;
  return `hsl(${hue}, 70%, 50%)`;
};

export const truncateText = (text, maxLength) => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

export const throttle = (func, limit) => {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

export const deepClone = (obj) => {
  return JSON.parse(JSON.stringify(obj));
};

export const mergeDeep = (target, source) => {
  const output = Object.assign({}, target);
  if (isObject(target) && isObject(source)) {
    Object.keys(source).forEach(key => {
      if (isObject(source[key])) {
        if (!(key in target))
          Object.assign(output, { [key]: source[key] });
        else
          output[key] = mergeDeep(target[key], source[key]);
      } else {
        Object.assign(output, { [key]: source[key] });
      }
    });
  }
  return output;
};

const isObject = (item) => {
  return item && typeof item === 'object' && !Array.isArray(item);
};

export const groupBy = (array, key) => {
  return array.reduce((result, currentValue) => {
    (result[currentValue[key]] = result[currentValue[key]] || []).push(currentValue);
    return result;
  }, {});
};

export const sortBy = (array, key, direction = 'asc') => {
  return array.sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];
    
    if (direction === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });
};

export const filterBy = (array, filters) => {
  return array.filter(item => {
    return Object.keys(filters).every(key => {
      if (filters[key] === null || filters[key] === undefined || filters[key] === '') {
        return true;
      }
      
      if (typeof filters[key] === 'string') {
        return item[key]?.toString().toLowerCase().includes(filters[key].toLowerCase());
      }
      
      return item[key] === filters[key];
    });
  });
};

export const createWebSocketConnection = (url, onMessage, onError, onClose) => {
  const ws = new WebSocket(url);
  
  ws.onopen = () => {
    console.log('WebSocket connected');
  };
  
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
    console.log('WebSocket disconnected');
    if (onClose) onClose();
  };
  
  return ws;
};

export const retry = async (fn, maxAttempts = 3, delay = 1000) => {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxAttempts) {
        throw error;
      }
      await new Promise(resolve => setTimeout(resolve, delay * attempt));
    }
  }
};

export const isValidIPAddress = (ip) => {
  const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
  const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;
  
  return ipv4Regex.test(ip) || ipv6Regex.test(ip);
};

export const parseHashType = (hash) => {
  const hashLengths = {
    32: 'MD5',
    40: 'SHA1',
    64: 'SHA256',
    128: 'SHA512',
  };
  
  return hashLengths[hash.length] || 'Unknown';
};

export const generateMockData = (type, count = 10) => {
  const mockGenerators = {
    nodes: () => ({
      id: Math.random().toString(36).substr(2, 9),
      hostname: `node-${Math.floor(Math.random() * 1000)}`,
      ip_address: `192.168.1.${Math.floor(Math.random() * 254) + 1}`,
      status: ['online', 'offline', 'working'][Math.floor(Math.random() * 3)],
      cpu_usage: Math.random() * 100,
      ram_usage: Math.random() * 100,
      disk_usage: Math.random() * 100,
    }),
    jobs: () => ({
      id: Math.random().toString(36).substr(2, 9),
      name: `Job ${Math.floor(Math.random() * 1000)}`,
      status: ['running', 'completed', 'failed', 'pending'][Math.floor(Math.random() * 4)],
      progress: Math.random() * 100,
      created_at: new Date(Date.now() - Math.random() * 86400000 * 7).toISOString(),
    }),
  };
  
  return Array.from({ length: count }, () => mockGenerators[type]?.() || {});
};