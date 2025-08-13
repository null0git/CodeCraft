# CrackPi Mobile

A comprehensive mobile application for remote monitoring and management of the CrackPi distributed password cracking platform.

## Features

### 🎯 Core Functionality
- **Real-time Dashboard**: Live monitoring of cluster status, active jobs, and system metrics
- **Cluster Management**: Monitor cluster health, leader election, and automatic failover
- **Node Management**: View and manage individual Raspberry Pi nodes with detailed metrics
- **Job Control**: Create, monitor, and manage password cracking jobs remotely
- **Terminal Access**: Execute commands on remote nodes through web-based terminal

### 📱 Mobile-Optimized Features
- **Push Notifications**: Receive alerts for job completion, password discoveries, and system events
- **Offline Support**: Basic functionality available without network connection
- **Touch-Friendly Interface**: Optimized for mobile interaction with gesture support
- **Dark/Light Mode**: Automatic theme switching based on system preferences
- **Performance Charts**: Real-time visualization of system metrics and job progress

### 🔐 Security & Authentication
- **Secure Authentication**: Token-based authentication with session management
- **Role-Based Access**: Admin and user roles with appropriate permissions
- **Encrypted Communication**: All data transmission encrypted via HTTPS/WSS
- **Biometric Authentication**: Optional fingerprint/face ID support (future feature)

## Installation

### Prerequisites
- Node.js 16.x or higher
- Expo CLI (`npm install -g expo-cli`)
- iOS Simulator (for iOS development)
- Android Studio (for Android development)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mobile_app
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your server configuration
   ```

4. **Start development server**
   ```bash
   npm start
   ```

5. **Run on device/simulator**
   ```bash
   # iOS
   npm run ios
   
   # Android
   npm run android
   
   # Web (for testing)
   npm run web
   ```

## Configuration

### Server Connection
The app can be configured to connect to your CrackPi server:

1. **Default Configuration**: `http://localhost:5000`
2. **Custom Server**: Configure in login screen settings
3. **Auto-Discovery**: Automatic detection of servers on local network

### Environment Variables
Create a `.env` file with the following variables:

```env
# Server Configuration
DEFAULT_SERVER_URL=http://localhost:5000
API_TIMEOUT=10000
WEBSOCKET_RECONNECT_INTERVAL=5000

# Notification Configuration
ENABLE_PUSH_NOTIFICATIONS=true
NOTIFICATION_SOUND=true
NOTIFICATION_VIBRATION=true

# Feature Flags
ENABLE_DARK_MODE=true
ENABLE_BIOMETRIC_AUTH=false
ENABLE_OFFLINE_MODE=true
ENABLE_ANALYTICS=false

# Debug
DEBUG_MODE=false
LOG_LEVEL=info
```

## Project Structure

```
mobile_app/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── charts/         # Chart components
│   │   ├── forms/          # Form components
│   │   └── common/         # Common UI elements
│   ├── screens/            # Screen components
│   │   ├── DashboardScreen.js
│   │   ├── ClusterScreen.js
│   │   ├── NodesScreen.js
│   │   ├── JobsScreen.js
│   │   └── SettingsScreen.js
│   ├── services/           # API and business logic
│   │   ├── ApiService.js   # REST API client
│   │   ├── AuthService.js  # Authentication
│   │   ├── NotificationService.js # Push notifications
│   │   └── WebSocketService.js # Real-time updates
│   ├── utils/              # Utility functions
│   │   ├── helpers.js      # General helpers
│   │   ├── formatters.js   # Data formatters
│   │   └── validators.js   # Input validation
│   ├── theme/              # App styling
│   │   ├── theme.js        # Theme configuration
│   │   └── styles.js       # Global styles
│   └── hooks/              # Custom React hooks
│       ├── useAuth.js      # Authentication hook
│       ├── useWebSocket.js # WebSocket hook
│       └── useNotifications.js # Notifications hook
├── assets/                 # Static assets
├── app.json               # Expo configuration
├── package.json           # Dependencies
└── README.md             # This file
```

## API Integration

The mobile app integrates with the CrackPi server through RESTful APIs and WebSocket connections:

### REST API Endpoints
- **Authentication**: `/auth/api/login`, `/auth/api/logout`
- **Dashboard**: `/api/dashboard/summary`
- **Cluster**: `/cluster/api/info`, `/cluster/api/status`, `/cluster/api/metrics`
- **Nodes**: `/api/clients`, `/api/clients/{id}`
- **Jobs**: `/api/jobs`, `/api/jobs/{id}/progress`
- **Terminal**: `/terminal/api/execute`

### WebSocket Connections
- **Real-time Updates**: Live system metrics and job progress
- **Notifications**: Instant alerts for system events
- **Terminal Sessions**: Interactive command execution

### Authentication Flow
1. User enters credentials in login screen
2. App sends login request to server
3. Server returns JWT token and user info
4. Token stored securely on device
5. Token included in all subsequent API requests

## Features Guide

### Dashboard
- **System Overview**: Total nodes, active jobs, cluster health
- **Performance Metrics**: CPU, memory, disk usage across cluster
- **Recent Activity**: Latest jobs and system events
- **Quick Actions**: Start new job, view cluster status

### Cluster Management
- **Leader Election**: View current leader, force new election
- **Node Health**: Monitor individual node status and metrics
- **Failover History**: Track automatic failover events
- **Network Topology**: Visual representation of cluster structure

### Node Management
- **Node List**: All connected Raspberry Pi devices
- **Individual Metrics**: CPU, RAM, disk, network for each node
- **Terminal Access**: Execute commands remotely
- **Performance History**: Historical metrics and trends

### Job Management
- **Job Creation**: Start new password cracking jobs
- **Progress Monitoring**: Real-time progress tracking
- **Result Viewing**: View cracked passwords and job statistics
- **Job Control**: Pause, resume, stop running jobs

### Settings
- **Server Configuration**: Change server URL and connection settings
- **Notifications**: Configure push notification preferences
- **Theme**: Switch between light and dark modes
- **Account**: User profile and authentication settings

## Development

### Running Tests
```bash
# Unit tests
npm test

# E2E tests (requires running server)
npm run test:e2e
```

### Building for Production
```bash
# Build for iOS
expo build:ios

# Build for Android
expo build:android

# Create standalone APK
expo build:android -t apk
```

### Debug Mode
Enable debug mode in `.env` file:
```env
DEBUG_MODE=true
LOG_LEVEL=debug
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify server URL is correct
   - Check network connectivity
   - Ensure server is running and accessible

2. **Authentication Errors**
   - Verify credentials are correct
   - Check server authentication configuration
   - Clear app data and try again

3. **Push Notifications Not Working**
   - Verify notification permissions are granted
   - Check notification service configuration
   - Test on physical device (not simulator)

4. **Performance Issues**
   - Enable performance profiling in debug mode
   - Check for memory leaks in network requests
   - Optimize image sizes and chart rendering

### Logs and Debugging
- Enable debug mode for detailed logging
- Use React Native Debugger for development
- Check server logs for API issues
- Monitor network requests in development tools

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the troubleshooting section above
- Review server documentation
- Contact the development team

## Roadmap

### Version 2.0 (Planned)
- Biometric authentication
- Offline job queue
- Advanced analytics dashboard
- Multi-server support
- Custom notification rules
- Voice commands integration
- AR node visualization

### Version 3.0 (Future)
- Machine learning job optimization
- Blockchain integration
- Cross-platform desktop app
- Advanced security features
- Cloud synchronization