from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging
from app import db
from models import Job, Hash, Client, JobLog
import json

logger = logging.getLogger(__name__)

progress_bp = Blueprint('progress', __name__, url_prefix='/progress')

@progress_bp.route('/')
@login_required
def index():
    """Real-time progress monitoring dashboard"""
    # Get active jobs
    active_jobs = Job.query.filter(Job.status.in_(['pending', 'running'])).all()
    
    # Get all clients with their current status
    clients = Client.query.order_by(Client.last_seen.desc()).all()
    
    return render_template('progress.html', 
                         active_jobs=active_jobs,
                         clients=clients)

@progress_bp.route('/job/<int:job_id>')
@login_required
def job_detail(job_id):
    """Detailed progress view for a specific job"""
    job = Job.query.get_or_404(job_id)
    
    # Check if user has access to this job
    if not current_user.is_admin and job.user_id != current_user.id:
        return "Access denied", 403
    
    # Get job progress data
    hashes = Hash.query.filter_by(job_id=job_id).all()
    assigned_clients = Client.query.filter_by(status='working').all()
    job_logs = JobLog.query.filter_by(job_id=job_id).order_by(JobLog.timestamp.desc()).limit(50).all()
    
    return render_template('job_progress.html',
                         job=job,
                         hashes=hashes,
                         assigned_clients=assigned_clients,
                         job_logs=job_logs)

@progress_bp.route('/api/job-status/<int:job_id>')
@login_required
def job_status_api(job_id):
    """API endpoint for real-time job status updates"""
    job = Job.query.get_or_404(job_id)
    
    # Check access
    if not current_user.is_admin and job.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Calculate progress statistics
    total_hashes = job.total_hashes or 0
    cracked_hashes = Hash.query.filter_by(job_id=job_id, is_cracked=True).count()
    
    # Get client progress data
    client_progress = []
    assigned_clients = Client.query.filter(Client.jobs.any(id=job_id)).all()
    
    for client in assigned_clients:
        # Calculate client-specific progress (this would be enhanced with actual range tracking)
        client_progress.append({
            'client_id': client.client_id,
            'hostname': client.hostname,
            'status': client.status,
            'progress_percent': calculate_client_progress(client, job),
            'current_attempt': get_client_current_attempt(client, job),
            'estimated_time_remaining': estimate_time_remaining(client, job),
            'cpu_usage': client.cpu_usage,
            'ram_usage': client.ram_usage,
            'last_seen': client.last_seen.isoformat() if client.last_seen else None
        })
    
    # Get recent cracked passwords
    recent_cracks = Hash.query.filter_by(job_id=job_id, is_cracked=True)\
                             .order_by(Hash.cracked_at.desc()).limit(5).all()
    
    return jsonify({
        'job_id': job_id,
        'status': job.status,
        'progress_percent': job.progress_percent or 0,
        'total_hashes': total_hashes,
        'cracked_hashes': cracked_hashes,
        'crack_rate': calculate_crack_rate(job),
        'estimated_completion': estimate_completion_time(job),
        'client_progress': client_progress,
        'recent_cracks': [{
            'hash_value': crack.hash_value[:16] + '...' if len(crack.hash_value) > 16 else crack.hash_value,
            'password': crack.cracked_password,
            'username': crack.username,
            'cracked_at': crack.cracked_at.isoformat() if crack.cracked_at else None,
            'cracked_by': crack.cracked_by_client.hostname if crack.cracked_by_client else 'Unknown'
        } for crack in recent_cracks],
        'last_updated': datetime.utcnow().isoformat()
    })

@progress_bp.route('/api/clients-status')
@login_required
def clients_status_api():
    """API endpoint for real-time client status updates"""
    clients = Client.query.all()
    
    client_data = []
    for client in clients:
        # Calculate client performance metrics
        avg_performance = calculate_client_performance(client)
        
        client_data.append({
            'id': client.id,
            'client_id': client.client_id,
            'hostname': client.hostname,
            'ip_address': client.ip_address,
            'mac_address': client.mac_address,
            'status': client.status,
            'cpu_model': client.cpu_model,
            'cpu_cores': client.cpu_cores,
            'cpu_frequency': client.cpu_frequency,
            'cpu_usage': client.cpu_usage,
            'ram_total': client.ram_total,
            'ram_usage': client.ram_usage,
            'disk_usage': client.disk_usage,
            'network_latency': client.network_latency,
            'last_seen': client.last_seen.isoformat() if client.last_seen else None,
            'uptime': calculate_uptime(client),
            'performance_score': avg_performance,
            'current_job': get_current_job(client),
            'total_jobs_completed': count_completed_jobs(client),
            'total_hashes_cracked': count_cracked_hashes(client)
        })
    
    return jsonify({
        'clients': client_data,
        'summary': {
            'total_clients': len(clients),
            'connected_clients': len([c for c in clients if c.status == 'connected']),
            'working_clients': len([c for c in clients if c.status == 'working']),
            'idle_clients': len([c for c in clients if c.status == 'connected']),
            'disconnected_clients': len([c for c in clients if c.status == 'disconnected'])
        },
        'last_updated': datetime.utcnow().isoformat()
    })

@progress_bp.route('/api/system-stats')
@login_required
def system_stats_api():
    """API endpoint for overall system statistics"""
    # Calculate system-wide statistics
    total_jobs = Job.query.count()
    active_jobs = Job.query.filter(Job.status.in_(['pending', 'running'])).count()
    completed_jobs = Job.query.filter_by(status='completed').count()
    failed_jobs = Job.query.filter_by(status='failed').count()
    
    total_hashes = Hash.query.count()
    cracked_hashes = Hash.query.filter_by(is_cracked=True).count()
    
    # Calculate crack rate over last 24 hours
    yesterday = datetime.utcnow() - timedelta(hours=24)
    recent_cracks = Hash.query.filter(
        Hash.is_cracked == True,
        Hash.cracked_at >= yesterday
    ).count()
    
    # Get top performing clients
    top_clients = get_top_performing_clients(5)
    
    return jsonify({
        'jobs': {
            'total': total_jobs,
            'active': active_jobs,
            'completed': completed_jobs,
            'failed': failed_jobs,
            'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        },
        'hashes': {
            'total': total_hashes,
            'cracked': cracked_hashes,
            'crack_rate': (cracked_hashes / total_hashes * 100) if total_hashes > 0 else 0,
            'recent_cracks_24h': recent_cracks
        },
        'top_clients': top_clients,
        'last_updated': datetime.utcnow().isoformat()
    })

# Helper functions for calculations

def calculate_client_progress(client, job):
    """Calculate progress percentage for a specific client on a job"""
    # This would be enhanced with actual range tracking
    # For now, return a simulated progress based on job overall progress
    if job.progress_percent:
        # Add some variance per client
        variance = hash(client.client_id) % 10 - 5  # -5 to +5
        return max(0, min(100, job.progress_percent + variance))
    return 0

def get_client_current_attempt(client, job):
    """Get current password being attempted by client"""
    # This would be enhanced with real-time tracking
    return f"Attempting range for {client.hostname}"

def estimate_time_remaining(client, job):
    """Estimate time remaining for client to complete its range"""
    # This would be calculated based on actual progress rate
    if job.estimated_time and job.progress_percent:
        remaining_percent = 100 - job.progress_percent
        total_estimated = job.estimated_time
        return int(total_estimated * (remaining_percent / 100))
    return None

def calculate_crack_rate(job):
    """Calculate current crack rate for the job"""
    if job.started_at:
        elapsed = (datetime.utcnow() - job.started_at).total_seconds()
        cracked_count = Hash.query.filter_by(job_id=job.id, is_cracked=True).count()
        if elapsed > 0:
            return cracked_count / elapsed * 3600  # per hour
    return 0

def estimate_completion_time(job):
    """Estimate job completion time"""
    if job.progress_percent and job.progress_percent > 0 and job.started_at:
        elapsed = (datetime.utcnow() - job.started_at).total_seconds()
        total_estimated = elapsed * (100 / job.progress_percent)
        completion_time = job.started_at + timedelta(seconds=total_estimated)
        return completion_time.isoformat()
    return None

def calculate_client_performance(client):
    """Calculate overall performance score for client"""
    # Base score on CPU, RAM, and historical performance
    cpu_score = (client.cpu_cores or 1) * (client.cpu_frequency or 1000) / 1000
    ram_score = (client.ram_total or 1000000000) / 1000000000  # GB
    uptime_score = min(100, calculate_uptime(client) / 3600)  # Hours to percentage
    
    return (cpu_score + ram_score + uptime_score) / 3

def calculate_uptime(client):
    """Calculate client uptime in seconds"""
    if client.last_seen and client.created_at:
        return (client.last_seen - client.created_at).total_seconds()
    return 0

def get_current_job(client):
    """Get current job for client"""
    current_job = Job.query.filter(
        Job.status.in_(['running', 'pending']),
        Job.client_id == client.id
    ).first()
    
    if current_job:
        return {
            'id': current_job.id,
            'name': current_job.name,
            'progress': current_job.progress_percent
        }
    return None

def count_completed_jobs(client):
    """Count completed jobs for client"""
    return Job.query.filter_by(client_id=client.id, status='completed').count()

def count_cracked_hashes(client):
    """Count hashes cracked by client"""
    return Hash.query.filter_by(cracked_by_client_id=client.id, is_cracked=True).count()

def get_top_performing_clients(limit=5):
    """Get top performing clients"""
    clients = Client.query.all()
    
    # Calculate performance scores and sort
    client_scores = []
    for client in clients:
        hashes_cracked = count_cracked_hashes(client)
        jobs_completed = count_completed_jobs(client)
        performance_score = calculate_client_performance(client)
        
        total_score = hashes_cracked * 10 + jobs_completed * 5 + performance_score
        
        client_scores.append({
            'hostname': client.hostname,
            'client_id': client.client_id,
            'hashes_cracked': hashes_cracked,
            'jobs_completed': jobs_completed,
            'performance_score': performance_score,
            'total_score': total_score,
            'status': client.status
        })
    
    # Sort by total score and return top performers
    client_scores.sort(key=lambda x: x['total_score'], reverse=True)
    return client_scores[:limit]