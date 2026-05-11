from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Client, Job, Hash, JobLog, HashType
from datetime import datetime, timedelta
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

@api_bp.route('/clients/disconnect', methods=['POST'])
def client_disconnect():
    """Client notifies server it is going offline gracefully"""
    data = request.get_json(silent=True) or {}
    client_id = data.get('client_id')
    if client_id:
        client = Client.query.filter_by(client_id=client_id).first()
        if client:
            client.status = 'offline'
            client.last_seen = datetime.utcnow()
            # Fail any running jobs for this client
            running_jobs = Job.query.filter_by(client_id=client.id, status='running').all()
            for job in running_jobs:
                job.status = 'failed'
                job.completed_at = datetime.utcnow()
                log_entry = JobLog()
                log_entry.job_id = job.id
                log_entry.client_id = client.id
                log_entry.level = 'warning'
                log_entry.message = 'Client disconnected — job marked failed'
                db.session.add(log_entry)
            db.session.commit()
            logger.info(f"Client disconnected gracefully: {client_id}")
    return jsonify({'status': 'ok'})

@api_bp.route('/clients/heartbeat', methods=['POST'])
def client_heartbeat():
    """Receive heartbeat from client and dispatch pending jobs"""
    data = request.get_json()
    client_id = data.get('client_id')

    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    # Update status — keep 'working' if client reports it, else 'online'
    reported_status = data.get('status', 'online')
    client.status = reported_status if reported_status in ('working', 'online', 'idle') else 'online'
    client.last_seen = datetime.utcnow()

    # Update metrics if provided
    metrics = data.get('system_metrics', {})
    if metrics:
        client.cpu_usage = metrics.get('cpu_usage', 0)
        client.ram_usage = metrics.get('memory_usage', 0)
        client.disk_usage = metrics.get('disk_usage', 0)
        client.network_latency = metrics.get('network_latency', 0)

    commands = []

    # Dispatch a pending job if client is idle
    if client.status in ('online', 'idle'):
        pending_job = Job.query.filter_by(status='pending', client_id=None).order_by(
            Job.priority.asc(), Job.created_at.asc()
        ).first()

        if pending_job:
            pending_job.client_id = client.id
            pending_job.status = 'running'
            pending_job.started_at = datetime.utcnow()
            client.status = 'working'

            # Collect hashes for the job
            hashes = Hash.query.filter_by(job_id=pending_job.id, is_cracked=False).all()
            hash_list = [{'id': h.id, 'hash': h.hash_value, 'salt': h.salt, 'username': h.username}
                         for h in hashes]

            hash_type_rec = HashType.query.get(pending_job.hash_type_id)
            commands.append({
                'command': 'start_job',
                'job_id': pending_job.id,
                'job_name': pending_job.name,
                'hash_type': hash_type_rec.name if hash_type_rec else 'unknown',
                'hashcat_mode': hash_type_rec.hashcat_mode if hash_type_rec else None,
                'john_format': hash_type_rec.john_format if hash_type_rec else None,
                'attack_mode': pending_job.attack_mode,
                'wordlist_path': pending_job.wordlist_path,
                'rules_path': pending_job.rules_path,
                'mask': pending_job.mask,
                'hashes': hash_list
            })

            log_entry = JobLog()
            log_entry.job_id = pending_job.id
            log_entry.client_id = client.id
            log_entry.level = 'info'
            log_entry.message = f'Job dispatched to client {client.hostname or client.client_id}'
            db.session.add(log_entry)

    db.session.commit()

    return jsonify({'status': 'ok', 'commands': commands})


@api_bp.route('/clients/timeout_check', methods=['POST'])
@login_required
def timeout_check():
    """Mark clients as offline if they haven't sent a heartbeat recently"""
    timeout_minutes = int(request.get_json().get('timeout_minutes', 5))
    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)

    stale = Client.query.filter(
        Client.last_seen < cutoff,
        Client.status.in_(('online', 'connected', 'idle', 'working'))
    ).all()

    timed_out = []
    for c in stale:
        # Fail any running jobs for this client
        running = Job.query.filter_by(client_id=c.id, status='running').all()
        for job in running:
            job.status = 'failed'
            job.completed_at = datetime.utcnow()
            log_entry = JobLog()
            log_entry.job_id = job.id
            log_entry.client_id = c.id
            log_entry.level = 'error'
            log_entry.message = f'Client timed out — job marked failed'
            db.session.add(log_entry)
        c.status = 'offline'
        timed_out.append(c.client_id)

        # Email notification for client going offline
        try:
            from utils.notifications import notify_client_offline
            from models import Settings
            def _gs(key, d=''):
                s = Settings.query.filter_by(key=key).first()
                return s.value if s else d
            if _gs('notify_client_offline', 'false') == 'true':
                notify_email = _gs('notify_email')
                if notify_email:
                    notify_client_offline(c, notify_email)
        except Exception:
            pass

    db.session.commit()
    return jsonify({'timed_out': timed_out, 'count': len(timed_out)})


@api_bp.route('/jobs/<int:job_id>/status', methods=['POST'])
def update_job_status(job_id):
    """Client reports job status update"""
    data = request.get_json()
    job = Job.query.get_or_404(job_id)

    new_status = data.get('status')
    if new_status in ('completed', 'failed', 'cancelled', 'running'):
        job.status = new_status
        if new_status == 'completed':
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.actual_time = int((job.completed_at - job.started_at).total_seconds())
            if job.assigned_client:
                job.assigned_client.status = 'online'
        elif new_status == 'failed':
            job.completed_at = datetime.utcnow()
            if job.assigned_client:
                job.assigned_client.status = 'online'

    details = data.get('details', {})
    if details.get('message'):
        log_entry = JobLog()
        log_entry.job_id = job.id
        log_entry.client_id = job.client_id
        log_entry.level = details.get('level', 'info')
        log_entry.message = details['message']
        db.session.add(log_entry)

    db.session.commit()
    return jsonify({'status': 'ok'})


@api_bp.route('/jobs/<int:job_id>/progress', methods=['POST'])
def update_job_progress(job_id):
    """Client reports cracking progress"""
    data = request.get_json()
    job = Job.query.get_or_404(job_id)

    progress = data.get('progress_percent')
    if progress is not None:
        job.progress_percent = float(progress)

    cracked_count = Hash.query.filter_by(job_id=job_id, is_cracked=True).count()
    job.cracked_hashes = cracked_count
    if job.total_hashes and job.total_hashes > 0:
        job.progress_percent = (cracked_count / job.total_hashes) * 100

    db.session.commit()
    return jsonify({'status': 'ok'})


@api_bp.route('/jobs/<int:job_id>/password-found', methods=['POST'])
def password_found(job_id):
    """Client reports a cracked password"""
    data = request.get_json()
    job = Job.query.get_or_404(job_id)

    hash_value = data.get('hash_value', '').strip()
    password = data.get('password', '').strip()
    client_id_str = data.get('client_id')

    if not hash_value or not password:
        return jsonify({'error': 'hash_value and password are required'}), 400

    hash_obj = Hash.query.filter_by(job_id=job_id, hash_value=hash_value).first()
    if hash_obj:
        hash_obj.is_cracked = True
        hash_obj.cracked_password = password
        hash_obj.cracked_at = datetime.utcnow()

        if client_id_str:
            client = Client.query.filter_by(client_id=client_id_str).first()
            if client:
                hash_obj.cracked_by_client_id = client.id

        # Update job stats
        cracked_count = Hash.query.filter_by(job_id=job_id, is_cracked=True).count()
        job.cracked_hashes = cracked_count + 1
        if job.total_hashes and job.total_hashes > 0:
            job.progress_percent = ((cracked_count + 1) / job.total_hashes) * 100

        log_entry = JobLog()
        log_entry.job_id = job.id
        log_entry.level = 'info'
        log_entry.message = f'Password cracked: {hash_value[:16]}... → {password}'
        db.session.add(log_entry)

        db.session.commit()
        return jsonify({'status': 'ok', 'cracked': True})

    return jsonify({'error': 'Hash not found in job'}), 404


@api_bp.route('/clients/<client_id>/jobs', methods=['GET'])
def get_client_jobs(client_id):
    """Get pending/assigned jobs for a specific client"""
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    jobs = Job.query.filter_by(client_id=client.id, status='running').all()
    job_data = []
    for job in jobs:
        hashes = Hash.query.filter_by(job_id=job.id, is_cracked=False).all()
        hash_type_rec = HashType.query.get(job.hash_type_id)
        job_data.append({
            'job_id': job.id,
            'job_name': job.name,
            'hash_type': hash_type_rec.name if hash_type_rec else 'unknown',
            'hashcat_mode': hash_type_rec.hashcat_mode if hash_type_rec else None,
            'john_format': hash_type_rec.john_format if hash_type_rec else None,
            'attack_mode': job.attack_mode,
            'wordlist_path': job.wordlist_path,
            'rules_path': job.rules_path,
            'mask': job.mask,
            'hashes': [{'id': h.id, 'hash': h.hash_value, 'salt': h.salt, 'username': h.username}
                       for h in hashes]
        })

    return jsonify({'jobs': job_data})

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

ONLINE_STATUSES = ('online', 'connected', 'idle', 'working')

@api_bp.route('/stats')
@login_required
def get_stats():
    """Get system statistics"""
    try:
        # Client statistics
        total_clients = Client.query.count()
        connected_clients = Client.query.filter(Client.status.in_(ONLINE_STATUSES)).count()
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
        clients = Client.query.filter(Client.status.in_(ONLINE_STATUSES)).all()
        
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
