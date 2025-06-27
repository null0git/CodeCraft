from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from models import Client, Job
from utils.network_utils import scan_network, get_network_info
import logging

logger = logging.getLogger(__name__)

clients_bp = Blueprint('clients', __name__, url_prefix='/clients')

@clients_bp.route('/')
@login_required
def index():
    # Get all clients
    clients = Client.query.order_by(Client.last_seen.desc()).all()
    
    # Calculate statistics
    connected_count = sum(1 for c in clients if c.status == 'connected')
    working_count = sum(1 for c in clients if c.status == 'working')
    idle_count = connected_count - working_count
    disconnected_count = sum(1 for c in clients if c.status == 'disconnected')
    
    return render_template('clients.html',
                         clients=clients,
                         connected_count=connected_count,
                         working_count=working_count,
                         idle_count=idle_count,
                         disconnected_count=disconnected_count)

@clients_bp.route('/scan_network', methods=['POST'])
@login_required
def scan_network_route():
    """Scan the network for potential clients"""
    try:
        network_info = get_network_info()
        if not network_info:
            return jsonify({'error': 'Unable to determine network information'}), 500
        
        # Scan for active hosts
        active_hosts = scan_network(network_info['network'])
        
        result = {
            'network': network_info['network'],
            'active_hosts': len(active_hosts),
            'hosts': active_hosts
        }
        
        flash(f'Network scan completed. Found {len(active_hosts)} active hosts.', 'info')
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error scanning network: {e}")
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/client/<client_id>')
@login_required
def client_details(client_id):
    """Get detailed information about a specific client"""
    client = Client.query.filter_by(client_id=client_id).first_or_404()
    
    # Get client's job history
    jobs = Job.query.filter_by(client_id=client.id).order_by(Job.created_at.desc()).limit(20).all()
    
    return jsonify({
        'client': {
            'id': client.id,
            'client_id': client.client_id,
            'hostname': client.hostname,
            'ip_address': client.ip_address,
            'mac_address': client.mac_address,
            'cpu_model': client.cpu_model,
            'cpu_cores': client.cpu_cores,
            'cpu_frequency': client.cpu_frequency,
            'ram_total': client.ram_total,
            'disk_total': client.disk_total,
            'os_info': client.os_info,
            'username': client.username,
            'status': client.status,
            'last_seen': client.last_seen.isoformat() if client.last_seen else None,
            'created_at': client.created_at.isoformat() if client.created_at else None,
            'cpu_usage': client.cpu_usage,
            'ram_usage': client.ram_usage,
            'disk_usage': client.disk_usage,
            'network_latency': client.network_latency
        },
        'jobs': [{
            'id': job.id,
            'name': job.name,
            'status': job.status,
            'progress_percent': job.progress_percent,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        } for job in jobs]
    })

@clients_bp.route('/client/<client_id>/stop', methods=['POST'])
@login_required
def stop_client(client_id):
    """Stop a working client"""
    client = Client.query.filter_by(client_id=client_id).first_or_404()
    
    if client.status != 'working':
        return jsonify({'error': 'Client is not currently working'}), 400
    
    try:
        # Find and cancel the running job
        job = Job.query.filter_by(client_id=client.id, status='running').first()
        if job:
            job.status = 'cancelled'
            job.completed_at = datetime.utcnow()
            
        # Update client status
        client.status = 'connected'
        
        db.session.commit()
        
        # Send stop command to client (socketio disabled temporarily)
        # socketio.emit('job_cancelled', {'job_id': job.id if job else None}, room=client_id)
        
        flash(f'Client {client.hostname or client.client_id} stopped successfully.', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error stopping client {client_id}: {e}")
        return jsonify({'error': str(e)}), 500

@clients_bp.route('/client/<client_id>/terminal')
@login_required
def client_terminal(client_id):
    """Open terminal session with client (placeholder)"""
    client = Client.query.filter_by(client_id=client_id).first_or_404()
    
    # This is a placeholder for terminal functionality
    # In a real implementation, you would set up a WebSocket connection
    # to provide shell access using something like xterm.js
    
    return jsonify({
        'message': 'Terminal access not yet implemented',
        'client_id': client_id,
        'client_hostname': client.hostname
    })

@clients_bp.route('/remove_client/<client_id>', methods=['POST'])
@login_required
def remove_client(client_id):
    """Remove a disconnected client from the database"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    client = Client.query.filter_by(client_id=client_id).first_or_404()
    
    if client.status in ['connected', 'working']:
        return jsonify({'error': 'Cannot remove connected client'}), 400
    
    # Check if client has running jobs
    running_jobs = Job.query.filter_by(client_id=client.id, status='running').count()
    if running_jobs > 0:
        return jsonify({'error': f'Client has {running_jobs} running jobs'}), 400
    
    try:
        db.session.delete(client)
        db.session.commit()
        
        flash(f'Client {client.hostname or client.client_id} removed successfully.', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error removing client {client_id}: {e}")
        return jsonify({'error': str(e)}), 500
