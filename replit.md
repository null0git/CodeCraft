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
- **WebSocket-based**: Real-time bidirectional communication between server and clients
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
- June 27, 2025: Complete implementation of distributed password cracking system with all enhanced features from comprehensive prompt
- June 27, 2025: Added range distribution, real-time monitoring, dark/light mode, network scanning, and advanced client capabilities

## User Preferences

Preferred communication style: Simple, everyday language.
Implementation approach: Comprehensive feature implementation with professional UI and production-ready deployment.