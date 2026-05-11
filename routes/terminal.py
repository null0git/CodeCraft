"""
Terminal Integration Routes for CrackPi
Provides web-based terminal access to connected clients
"""

from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
import json
import time
import logging
from models import Client
from app import db

terminal_bp = Blueprint('terminal', __name__, url_prefix='/terminal')
logger = logging.getLogger(__name__)

# Store active terminal sessions
terminal_sessions = {}
command_queue = {}
command_responses = {}

@terminal_bp.route('/')
@login_required
def terminal_dashboard():
    """Terminal dashboard showing available clients"""
    clients = Client.query.filter(Client.status.in_(['online', 'connected', 'idle', 'working'])).all()
    return render_template('terminal/dashboard.html', clients=clients)

@terminal_bp.route('/client/<client_id>')
@login_required
def client_terminal(client_id):
    """Web terminal for specific client"""
    client = Client.query.filter_by(client_id=client_id).first_or_404()
    
    # Create new terminal session
    session_id = f"{current_user.id}_{client_id}_{int(time.time())}"
    terminal_sessions[session_id] = {
        'client_id': client_id,
        'user_id': current_user.id,
        'created_at': time.time(),
        'last_activity': time.time()
    }
    
    return render_template('terminal/client_terminal.html', 
                         client=client, session_id=session_id)

@terminal_bp.route('/api/execute', methods=['POST'])
@login_required
def execute_command():
    """Execute command on remote client"""
    data = request.get_json()
    session_id = data.get('session_id')
    command = data.get('command', '').strip()
    client_id = data.get('client_id')
    
    if not session_id or not command or not client_id:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Validate session
    if session_id not in terminal_sessions:
        return jsonify({'error': 'Invalid terminal session'}), 401
    
    session_data = terminal_sessions[session_id]
    if session_data['user_id'] != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Update session activity
    session_data['last_activity'] = time.time()
    
    # Queue command for client
    command_id = f"{session_id}_{int(time.time())}"
    
    if client_id not in command_queue:
        command_queue[client_id] = []
    
    command_queue[client_id].append({
        'command_id': command_id,
        'session_id': session_id,
        'command': command,
        'timestamp': time.time(),
        'user_id': current_user.id
    })
    
    logger.info(f"Queued command for client {client_id}: {command}")
    
    return jsonify({
        'status': 'queued',
        'command_id': command_id,
        'message': 'Command queued for execution'
    })

@terminal_bp.route('/api/commands/<client_id>')
def get_pending_commands(client_id):
    """Get pending commands for client (called by client)"""
    commands = command_queue.get(client_id, [])
    
    # Clear the queue after returning commands
    command_queue[client_id] = []
    
    return jsonify({'commands': commands})

@terminal_bp.route('/api/response', methods=['POST'])
def receive_command_response():
    """Receive command response from client"""
    data = request.get_json()
    command_id = data.get('command_id')
    session_id = data.get('session_id')
    
    # Store response
    command_responses[command_id] = {
        'session_id': session_id,
        'stdout': data.get('stdout', ''),
        'stderr': data.get('stderr', ''),
        'return_code': data.get('return_code', 0),
        'timestamp': time.time()
    }
    
    logger.info(f"Received response for command {command_id}")
    
    return jsonify({'status': 'received'})

@terminal_bp.route('/api/poll/<session_id>')
@login_required
def poll_responses(session_id):
    """Poll for command responses"""
    if session_id not in terminal_sessions:
        return jsonify({'error': 'Invalid session'}), 401
    
    session_data = terminal_sessions[session_id]
    if session_data['user_id'] != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get responses for this session
    responses = []
    for command_id, response in list(command_responses.items()):
        if response['session_id'] == session_id:
            responses.append({
                'command_id': command_id,
                **response
            })
            # Remove processed response
            del command_responses[command_id]
    
    # Update session activity
    session_data['last_activity'] = time.time()
    
    return jsonify({'responses': responses})

@terminal_bp.route('/api/session/<session_id>/close', methods=['POST'])
def close_session(session_id):
    """Close terminal session — no login required (called via sendBeacon on page unload)"""
    if session_id in terminal_sessions:
        del terminal_sessions[session_id]
    return jsonify({'status': 'closed'})

@terminal_bp.route('/api/file-browser/<client_id>')
@login_required
def file_browser(client_id):
    """Get file browser data for client"""
    path = request.args.get('path', '/home/pi')
    
    # Queue ls command
    command_id = f"fb_{client_id}_{int(time.time())}"
    
    if client_id not in command_queue:
        command_queue[client_id] = []
    
    # Use ls -la to get detailed file information
    ls_command = f"ls -la '{path}' 2>/dev/null || echo 'Error: Cannot access directory'"
    
    command_queue[client_id].append({
        'command_id': command_id,
        'session_id': 'file_browser',
        'command': ls_command,
        'timestamp': time.time(),
        'user_id': current_user.id,
        'type': 'file_browser'
    })
    
    return jsonify({
        'status': 'queued',
        'command_id': command_id,
        'path': path
    })

@terminal_bp.route('/api/system-info/<client_id>')
@login_required
def get_system_info(client_id):
    """Get system information from client"""
    client = Client.query.filter_by(client_id=client_id).first_or_404()
    
    # Queue system info commands
    commands = [
        'uname -a',
        'cat /proc/cpuinfo | grep "model name" | head -1',
        'free -h',
        'df -h',
        'uptime',
        'ps aux | head -20'
    ]
    
    command_ids = []
    for cmd in commands:
        command_id = f"sysinfo_{client_id}_{int(time.time())}_{len(command_ids)}"
        command_ids.append(command_id)
        
        if client_id not in command_queue:
            command_queue[client_id] = []
        
        command_queue[client_id].append({
            'command_id': command_id,
            'session_id': 'system_info',
            'command': cmd,
            'timestamp': time.time(),
            'user_id': current_user.id,
            'type': 'system_info'
        })
    
    return jsonify({
        'status': 'queued',
        'command_ids': command_ids,
        'client_info': {
            'hostname': client.hostname,
            'ip_address': client.ip_address,
            'last_seen': client.last_seen.isoformat() if client.last_seen else None
        }
    })

# Cleanup old sessions periodically
@terminal_bp.before_app_request
def cleanup_old_sessions():
    """Clean up old terminal sessions"""
    current_time = time.time()
    timeout = 3600  # 1 hour timeout
    
    for session_id in list(terminal_sessions.keys()):
        session_data = terminal_sessions[session_id]
        if current_time - session_data['last_activity'] > timeout:
            del terminal_sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
    
    # Also cleanup old command responses
    for command_id in list(command_responses.keys()):
        response = command_responses[command_id]
        if current_time - response['timestamp'] > timeout:
            del command_responses[command_id]