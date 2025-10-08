# CrackPi - Distributed Password Cracking System

## Overview

CrackPi is a distributed password cracking platform designed to run on Raspberry Pi devices. The system consists of a main server that coordinates cracking jobs and multiple client nodes that perform the actual password cracking work. The platform provides a web-based interface for managing clients, jobs, and monitoring system performance.

## System Architecture

### Server Architecture
- **Flask Web Application**: Main server built with Flask framework providing RESTful APIs and web interface
- **SQLAlchemy ORM**: Database abstraction layer for managing users, clients, jobs, and hashes
- **Flask-SocketIO**: Real-time communication between server and clients using WebSocket connections
- **Gunicorn WSGI Server**: Production-grade web server for serving the Flask application
- **Template Engine**: Jinja2 templating with Bootstrap-based responsive dark theme UI

### Client Architecture
- **Python Daemon**: Standalone client daemon that connects to the main server
- **SocketIO Client**: Real-time communication with the server for job distribution and status updates
- **System Monitoring**: Built-in system metrics collection (CPU, RAM, disk usage)
- **Cracking Engine Integration**: Support for both John the Ripper and Hashcat password cracking tools

### Communication Protocol
- **HTTP REST API**: All client-server communication via standard REST endpoints
- **Heartbeat System**: Clients send periodic heartbeats with metrics and status updates
- **Command Queue**: Server sends commands to clients in heartbeat responses
- **RESTful APIs**: HTTP-based APIs for web interface interactions
- **Automatic Reconnection**: Clients automatically reconnect to server on network disruptions

## Key Components

### Web Interface
- **Dashboard**: Real-time overview of system status, connected clients, and active jobs
- **Client Management**: View and manage connected Raspberry Pi clients with detailed system information
- **Job Management**: Create, monitor, and manage password cracking jobs
- **User Management**: Authentication system with admin and regular user roles
- **Settings Panel**: System configuration and maintenance tools

### Database Schema
- **Users**: Authentication and authorization with role-based access
- **Clients**: Registration and status tracking of Raspberry Pi nodes
- **Jobs**: Password cracking job management with priority queuing
- **Hashes**: Individual hash storage with cracking status tracking
- **HashTypes**: Supported hash format definitions with tool-specific parameters

### Cracking Engine
- **Multi-tool Support**: Integration with both John the Ripper and Hashcat
- **Hash Type Detection**: Automatic identification of hash formats
- **Job Distribution**: Intelligent work distribution across available clients
- **Progress Tracking**: Real-time monitoring of cracking progress and results

### Network Management
- **Auto-discovery**: Network scanning to identify potential client devices
- **Client Registration**: Automatic client registration with unique identification
- **Health Monitoring**: Regular health checks and performance monitoring

## Data Flow

1. **Client Registration**: Raspberry Pi clients connect to server and register with system information
2. **Job Creation**: Users upload hash files and configure cracking parameters through web interface
3. **Job Distribution**: Server distributes hash subsets to available clients based on capacity
4. **Progress Monitoring**: Clients report progress and results back to server in real-time
5. **Result Aggregation**: Server collects and consolidates cracking results from all clients
6. **Notification**: Users receive notifications when passwords are cracked or jobs complete

## External Dependencies

### Python Packages
- **Flask Ecosystem**: flask, flask-sqlalchemy, flask-login, flask-socketio
- **Database**: psycopg2-binary for PostgreSQL support, SQLAlchemy for ORM
- **Networking**: python-socketio, netifaces, python-nmap for network operations
- **System Monitoring**: psutil for system metrics collection
- **Security**: werkzeug for password hashing, paramiko for SSH operations
- **Web Server**: gunicorn, eventlet for production deployment

### System Dependencies
- **Password Cracking Tools**: John the Ripper, Hashcat (installed via system packages)
- **Network Tools**: nmap for network scanning capabilities
- **Database**: PostgreSQL for production or SQLite for development
- **System Libraries**: OpenSSL for cryptographic operations

### Frontend Dependencies
- **UI Framework**: Bootstrap 5 with dark theme support
- **Icons**: Feather icons for consistent iconography
- **Charts**: Chart.js for real-time performance visualization
- **Terminal**: xterm.js for interactive client shell access (planned)

## Deployment Strategy

### Server Deployment
- **Systemd Service**: crackpi-server.service for automatic startup and management
- **Environment Configuration**: Environment variables for database and security settings
- **Resource Limits**: Memory and CPU quotas to prevent resource exhaustion
- **Security Hardening**: Restricted file system access and privilege separation

### Client Deployment
- **Systemd Service**: crackpi-client.service for daemon management
- **Auto-configuration**: Setup scripts for easy client deployment
- **Resource Optimization**: CPU quota allowing 95% usage for cracking operations
- **Automatic Recovery**: Service restart policies for fault tolerance

### Network Configuration
- **Service Discovery**: Automatic detection of server and client nodes
- **Port Management**: Configurable ports with default 5000 for web interface
- **Firewall Integration**: Documentation for required port openings

### Database Setup
- **SQLite Development**: File-based database for development and small deployments
- **PostgreSQL Production**: Scalable database solution for larger deployments
- **Migration Support**: Database schema versioning and upgrade paths

## Enhanced Features Implemented (June 27, 2025)

### Hash Cracking & Distribution Logic
- ✅ Range-based password distribution among multiple clients
- ✅ Support for custom ranges (e.g., 0000-9999) and charset-based generation
- ✅ Automatic hash type detection (MD5, SHA1, SHA256, SHA512, NTLM, bcrypt)
- ✅ Intelligent work distribution with remainder handling across any number of clients
- ✅ Real-time progress tracking and password found notifications

### Web-Based UI Enhancements
- ✅ Professional hash input page with live range distribution preview
- ✅ Real-time progress monitor with visual indicators and client status
- ✅ Dark/light mode toggle with persistent theme preferences
- ✅ Enhanced client dashboard with system metrics and performance monitoring
- ✅ Interactive client management with terminal access capabilities
- ✅ Auto-detecting hash type input with manual override options

### Advanced Client Behavior
- ✅ Enhanced client with automatic server discovery and reconnection
- ✅ Comprehensive system information collection (CPU, RAM, disk, network)
- ✅ Range-based distributed cracking with progress callbacks
- ✅ Automatic health monitoring and performance metrics reporting
- ✅ Support for multiple cracking tools (Python hashlib, Hashcat, John the Ripper)

### Network & Deployment Features
- ✅ Advanced network scanning utility for client discovery
- ✅ Auto-start script for seamless server deployment
- ✅ Systemd service configurations for both server and clients
- ✅ Professional responsive UI with Bootstrap dark theme
- ✅ Real-time updates and live monitoring capabilities

### Technical Deliverables
- ✅ Enhanced range distribution algorithms with mathematical precision
- ✅ Professional web interface with real-time updates
- ✅ Comprehensive network scanning and client discovery
- ✅ Production-ready deployment scripts and configurations
- ✅ Advanced progress monitoring with visual indicators
- ✅ Dark/light theme toggle functionality

## Changelog
- October 8, 2025: **Critical Communication Fix** - Replaced SocketIO with HTTP REST API for reliable client-server communication
- October 8, 2025: Updated setup scripts to auto-generate service files with detected paths (no manual configuration needed)
- October 8, 2025: Fixed package conflicts and JavaScript errors, server and clients now communicate correctly
- August 13, 2025: Complete system integration with unified client-server communication, terminal access, and production deployment
- August 13, 2025: Fixed database connectivity issues with SQLite fallback, implemented comprehensive service files and setup scripts  
- August 13, 2025: Added full terminal integration with web-based client management and real-time command execution
- June 27, 2025: Complete implementation of distributed password cracking system with all enhanced features from comprehensive prompt
- June 27, 2025: Added range distribution, real-time monitoring, dark/light mode, network scanning, and advanced client capabilities

## Latest Implementation (August 13, 2025)

### Complete Production-Ready System
- ✅ **Database Integration**: SQLite with automatic fallback from PostgreSQL for reliable development and production deployment
- ✅ **Service Files**: Complete systemd service configurations for both server and client with resource management
- ✅ **Setup Scripts**: Professional installation scripts with dependency management and firewall configuration
- ✅ **Terminal Integration**: Full web-based terminal access with real-time command execution and response handling
- ✅ **Unified Communication**: Single client-server API with comprehensive heartbeat and job distribution system
- ✅ **Network Auto-Discovery**: Automatic server discovery and client registration with system information collection

### Professional Deployment Features
- ✅ **Production Scripts**: `setup_server.sh` and `setup_client.sh` with complete system configuration
- ✅ **Service Management**: Systemd services with automatic restart, resource limits, and security hardening
- ✅ **Network Configuration**: Nginx reverse proxy setup with WebSocket support for real-time communication
- ✅ **Security Features**: User privilege separation, restricted file system access, and firewall configuration
- ✅ **Monitoring Integration**: Comprehensive system metrics collection and real-time performance monitoring

### Advanced Features Implementation (August 13, 2025)
- ✅ **Advanced Password Cracking**: Multiple attack modes (dictionary, brute force, mask, hybrid, rule-based, markov, prince)
- ✅ **Universal Client**: Single script supporting enhanced and normal modes with auto-detection
- ✅ **User Detection**: Automatic user detection and path configuration for flexible installation
- ✅ **Multi-Hash Distribution**: Advanced algorithms for distributing hashes across multiple clients
- ✅ **Capability Detection**: Automatic GPU, CPU, and tool detection with performance optimization
- ✅ **Concurrent Jobs**: Support for multiple simultaneous cracking jobs per client
- ✅ **Advanced Algorithms**: Support for MD5, SHA1, SHA256, SHA512, NTLM, bcrypt, SHA3, Blake2b, Argon2

### Mobile App Implementation (August 13, 2025)
- ✅ **React Native Mobile App**: Complete mobile application for remote monitoring and management
- ✅ **Real-time Dashboard**: Live cluster status, metrics, and job monitoring with charts
- ✅ **Cluster Management**: Mobile cluster control with leader election and failover management
- ✅ **Node Management**: Full node monitoring with performance metrics and terminal access
- ✅ **Job Control**: Create, monitor, and manage cracking jobs from mobile device
- ✅ **Push Notifications**: Real-time alerts for job completion and system events
- ✅ **Authentication**: Secure login with token-based authentication and session management

### Current System Status
- **Server**: Running on Flask with SQLite database, accessible at http://localhost:5000
- **Default Login**: admin / admin123
- **Communication**: HTTP REST API (SocketIO removed due to package conflicts)
- **Client**: Uses client_server_api.py with automatic server discovery and HTTP communication
- **Setup Scripts**: Fully automated with auto-generated service files and path detection
- **Terminal Access**: Full web-based terminal with real-time command execution
- **Advanced Distribution**: Equal split, capability-based, dynamic load, and hash-based strategies
- **Database**: SQLite with automatic fallback and production-ready configuration
- **Mobile App**: React Native app with complete remote monitoring and management capabilities

## User Preferences

Preferred communication style: Simple, everyday language.
Implementation approach: Comprehensive feature implementation with professional UI and production-ready deployment.
System requirements: Complete self-contained solution with unified communication and terminal integration.