from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from models import Client, Job, Hash, User
from utils.system_utils import get_system_metrics

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Get client statistics
    connected_clients = Client.query.filter_by(status='connected').count()
    total_clients = Client.query.count()
    working_clients = Client.query.filter_by(status='working').count()
    idle_clients = connected_clients - working_clients
    
    # Get job statistics
    running_jobs = Job.query.filter_by(status='running').count()
    
    # Get passwords cracked today
    today = datetime.utcnow().date()
    cracked_today = Hash.query.filter(
        Hash.is_cracked == True,
        Hash.cracked_at >= today
    ).count()
    
    # Get recent jobs
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
    
    # Get recent cracked passwords
    recent_cracks = Hash.query.filter(
        Hash.is_cracked == True
    ).order_by(Hash.cracked_at.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         connected_clients=connected_clients,
                         total_clients=total_clients,
                         working_clients=working_clients,
                         idle_clients=idle_clients,
                         running_jobs=running_jobs,
                         cracked_today=cracked_today,
                         recent_jobs=recent_jobs,
                         recent_cracks=recent_cracks)

@dashboard_bp.route('/server_status')
@login_required
def server_status():
    """Get server system status for dashboard updates"""
    try:
        metrics = get_system_metrics()
        
        # Get client counts
        connected_clients = Client.query.filter_by(status='connected').count()
        working_clients = Client.query.filter_by(status='working').count()
        total_clients = Client.query.count()
        idle_clients = connected_clients - working_clients
        
        # Get job counts
        running_jobs = Job.query.filter_by(status='running').count()
        
        # Get passwords cracked today
        today = datetime.utcnow().date()
        cracked_today = Hash.query.filter(
            Hash.is_cracked == True,
            Hash.cracked_at >= today
        ).count()
        
        return {
            'server_metrics': metrics,
            'client_stats': {
                'connected': connected_clients,
                'working': working_clients,
                'total': total_clients,
                'idle': idle_clients
            },
            'job_stats': {
                'running': running_jobs
            },
            'crack_stats': {
                'today': cracked_today
            }
        }
    except Exception as e:
        return {'error': str(e)}, 500
