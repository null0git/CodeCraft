from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Client, Job, Hash, JobLog
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'CrackPi server is running',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@api_bp.route('/clients/register', methods=['POST'])
def register_client():
    """Register a new client"""
    data = request.get_json()
    client_id = data.get('client_id')
    system_info = data.get('system_info', {})
    
    # Check if client already exists
    client = Client.query.filter_by(client_id=client_id).first()
    
    if not client:
        # Create new client
        client = Client()
        client.client_id = client_id
        client.hostname = system_info.get('network', {}).get('hostname', 'Unknown')
        client.ip_address = system_info.get('network', {}).get('ip_address', '127.0.0.1')
        client.mac_address = system_info.get('network', {}).get('mac_address', '00:00:00:00:00:00')
        client.status = 'online'
        client.cpu_cores = system_info.get('cpu', {}).get('cores', 1)
        client.ram_total = system_info.get('memory', {}).get('total', 0)
        client.disk_total = system_info.get('disk', {}).get('total', 0)
        client.last_seen = datetime.utcnow()
        
        db.session.add(client)
        db.session.commit()
        
        logger.info(f"Registered new client: {client_id}")
    else:
        # Update existing client
        client.status = 'online'
        client.last_seen = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Updated existing client: {client_id}")
    
    return jsonify({'status': 'registered', 'client_id': client_id})

@api_bp.route('/clients/heartbeat', methods=['POST'])
def client_heartbeat():
    """Receive heartbeat from client"""
    data = request.get_json()
    client_id = data.get('client_id')
    
    client = Client.query.filter_by(client_id=client_id).first()
    if client:
        client.status = data.get('status', 'idle')
        client.last_seen = datetime.utcnow()
        
        # Update metrics if provided
        metrics = data.get('system_metrics', {})
        if metrics:
            client.cpu_usage = metrics.get('cpu_usage', 0)
            client.ram_usage = metrics.get('memory_usage', 0)
            client.disk_usage = metrics.get('disk_usage', 0)
            client.network_latency = metrics.get('network_latency', 0)
        
        db.session.commit()
        
        # Return any commands for the client
        return jsonify({
            'status': 'ok',
            'commands': []  # Commands would be queued here
        })
    
    return jsonify({'error': 'Client not found'}), 404

@api_bp.route('/clients')
@login_required
def get_clients():
    """Get all clients with their current status"""
    clients = Client.query.all()
    
    client_data = []
    for client in clients:
        client_data.append({
            'id': client.id,
            'client_id': client.client_id,
            'hostname': client.hostname,
            'ip_address': client.ip_address,
            'mac_address': client.mac_address,
            'status': client.status,
            'cpu_usage': client.cpu_usage,
            'ram_usage': client.ram_usage,
            'disk_usage': client.disk_usage,
            'network_latency': client.network_latency,
            'last_seen': client.last_seen.isoformat() if client.last_seen else None
        })
    
    return jsonify(client_data)

@api_bp.route('/jobs')
@login_required
def get_jobs():
    """Get jobs (filtered by user if not admin)"""
    if current_user.is_admin:
        jobs = Job.query.order_by(Job.created_at.desc()).all()
    else:
        jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).all()
    
    job_data = []
    for job in jobs:
        job_data.append({
            'id': job.id,
            'name': job.name,
            'status': job.status,
            'progress_percent': job.progress_percent,
            'total_hashes': job.total_hashes,
            'cracked_hashes': job.cracked_hashes,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'estimated_time': job.estimated_time,
            'client_id': job.assigned_client.client_id if job.assigned_client else None,
            'hash_type': job.hash_type.name
        })
    
    return jsonify(job_data)

@api_bp.route('/job/<int:job_id>/progress')
@login_required
def get_job_progress(job_id):
    """Get detailed progress for a specific job"""
    # Check permissions
    if current_user.is_admin:
        job = Job.query.get_or_404(job_id)
    else:
        job = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    
    # Get cracked hashes for this job
    cracked_hashes = Hash.query.filter_by(job_id=job_id, is_cracked=True).order_by(Hash.cracked_at.desc()).limit(10).all()
    
    # Get recent logs
    logs = JobLog.query.filter_by(job_id=job_id).order_by(JobLog.timestamp.desc()).limit(20).all()
    
    return jsonify({
        'job': {
            'id': job.id,
            'name': job.name,
            'status': job.status,
            'progress_percent': job.progress_percent,
            'total_hashes': job.total_hashes,
            'cracked_hashes': job.cracked_hashes,
            'estimated_time': job.estimated_time,
            'actual_time': job.actual_time
        },
        'recent_cracks': [{
            'hash_value': h.hash_value,
            'cracked_password': h.cracked_password,
            'cracked_at': h.cracked_at.isoformat() if h.cracked_at else None,
            'username': h.username
        } for h in cracked_hashes],
        'logs': [{
            'level': log.level,
            'message': log.message,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None
        } for log in logs]
    })

@api_bp.route('/stats')
@login_required
def get_stats():
    """Get system statistics"""
    try:
        # Client statistics
        total_clients = Client.query.count()
        connected_clients = Client.query.filter_by(status='connected').count()
        working_clients = Client.query.filter_by(status='working').count()
        
        # Job statistics
        if current_user.is_admin:
            total_jobs = Job.query.count()
            running_jobs = Job.query.filter_by(status='running').count()
            completed_jobs = Job.query.filter_by(status='completed').count()
            failed_jobs = Job.query.filter_by(status='failed').count()
        else:
            total_jobs = Job.query.filter_by(user_id=current_user.id).count()
            running_jobs = Job.query.filter_by(user_id=current_user.id, status='running').count()
            completed_jobs = Job.query.filter_by(user_id=current_user.id, status='completed').count()
            failed_jobs = Job.query.filter_by(user_id=current_user.id, status='failed').count()
        
        # Hash statistics
        total_hashes = Hash.query.count()
        cracked_hashes = Hash.query.filter_by(is_cracked=True).count()
        
        # Cracked today
        today = datetime.utcnow().date()
        cracked_today = Hash.query.filter(
            Hash.is_cracked == True,
            Hash.cracked_at >= today
        ).count()
        
        return jsonify({
            'clients': {
                'total': total_clients,
                'connected': connected_clients,
                'working': working_clients,
                'idle': connected_clients - working_clients
            },
            'jobs': {
                'total': total_jobs,
                'running': running_jobs,
                'completed': completed_jobs,
                'failed': failed_jobs,
                'pending': total_jobs - running_jobs - completed_jobs - failed_jobs
            },
            'hashes': {
                'total': total_hashes,
                'cracked': cracked_hashes,
                'cracked_today': cracked_today,
                'crack_rate': (cracked_hashes / total_hashes * 100) if total_hashes > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/system_status')
@login_required
def get_system_status():
    """Get real-time system status"""
    try:
        from utils.system_utils import get_system_metrics
        
        # Get server metrics
        server_metrics = get_system_metrics()
        
        # Get client metrics summary
        clients = Client.query.filter_by(status='connected').all()
        
        total_cpu = 0
        total_ram = 0
        total_disk = 0
        client_count = len(clients)
        
        for client in clients:
            total_cpu += client.cpu_usage or 0
            total_ram += client.ram_usage or 0
            total_disk += client.disk_usage or 0
        
        avg_metrics = {
            'cpu_usage': total_cpu / client_count if client_count > 0 else 0,
            'ram_usage': total_ram / client_count if client_count > 0 else 0,
            'disk_usage': total_disk / client_count if client_count > 0 else 0
        }
        
        return jsonify({
            'server_metrics': server_metrics,
            'client_metrics': avg_metrics,
            'client_count': client_count,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/recent_activity')
@login_required
def get_recent_activity():
    """Get recent system activity"""
    try:
        # Get recent job activity
        if current_user.is_admin:
            recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
        else:
            recent_jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).limit(5).all()
        
        # Get recent cracks
        recent_cracks = Hash.query.filter_by(is_cracked=True).order_by(Hash.cracked_at.desc()).limit(10).all()
        
        # Get recent client connections
        recent_clients = Client.query.order_by(Client.last_seen.desc()).limit(5).all()
        
        return jsonify({
            'recent_jobs': [{
                'id': job.id,
                'name': job.name,
                'status': job.status,
                'created_at': job.created_at.isoformat() if job.created_at else None
            } for job in recent_jobs],
            'recent_cracks': [{
                'hash_value': crack.hash_value[:16] + '...',
                'password': crack.cracked_password,
                'cracked_at': crack.cracked_at.isoformat() if crack.cracked_at else None,
                'job_name': crack.job.name if crack.job else None
            } for crack in recent_cracks],
            'recent_clients': [{
                'client_id': client.client_id,
                'hostname': client.hostname,
                'status': client.status,
                'last_seen': client.last_seen.isoformat() if client.last_seen else None
            } for client in recent_clients]
        })
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return jsonify({'error': str(e)}), 500
