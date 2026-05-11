from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from models import User, Settings, HashType
from config import Config
import logging

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


def get_setting(key, default=''):
    s = Settings.query.filter_by(key=key).first()
    return s.value if s else default


def set_setting(key, value, description=''):
    s = Settings.query.filter_by(key=key).first()
    if not s:
        s = Settings(key=key)
        db.session.add(s)
    s.value = value
    if description:
        s.description = description
    db.session.commit()


@settings_bp.route('/')
@login_required
def index():
    users = []
    if current_user.is_admin:
        users = User.query.order_by(User.created_at.desc()).all()

    settings = {}
    for s in Settings.query.all():
        settings[s.key] = s.value

    hash_types = HashType.query.all()

    # Load SMTP settings for the email tab
    smtp = {
        'host': get_setting('smtp_host'),
        'port': get_setting('smtp_port', '587'),
        'username': get_setting('smtp_username'),
        'from': get_setting('smtp_from'),
        'tls': get_setting('smtp_tls', 'true'),
        'notify_job_complete': get_setting('notify_job_complete', 'true'),
        'notify_job_failed': get_setting('notify_job_failed', 'true'),
        'notify_client_offline': get_setting('notify_client_offline', 'false'),
        'notify_client_online': get_setting('notify_client_online', 'false'),
        'notify_email': get_setting('notify_email'),
    }

    return render_template('settings.html',
                           users=users,
                           settings=settings,
                           hash_types=hash_types,
                           available_hash_types=Config.HASH_TYPES,
                           smtp=smtp)

@settings_bp.route('/update_setting', methods=['POST'])
@login_required
def update_setting():
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    key = request.form.get('key')
    value = request.form.get('value')
    description = request.form.get('description', '')
    
    if not key:
        return jsonify({'error': 'Setting key is required'}), 400
    
    try:
        # Get or create setting
        setting = Settings.query.filter_by(key=key).first()
        if not setting:
            setting = Settings(key=key)
            db.session.add(setting)
        
        setting.value = value
        setting.description = description
        
        db.session.commit()
        
        flash(f'Setting "{key}" updated successfully.', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/create_hash_type', methods=['POST'])
@login_required
def create_hash_type():
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    name = request.form.get('name')
    hashcat_mode = request.form.get('hashcat_mode')
    john_format = request.form.get('john_format')
    description = request.form.get('description', '')
    
    if not name:
        return jsonify({'error': 'Hash type name is required'}), 400
    
    # Check if hash type already exists
    if HashType.query.filter_by(name=name).first():
        return jsonify({'error': 'Hash type already exists'}), 400
    
    try:
        hash_type = HashType(
            name=name,
            hashcat_mode=int(hashcat_mode) if hashcat_mode else None,
            john_format=john_format,
            description=description
        )
        
        db.session.add(hash_type)
        db.session.commit()
        
        flash(f'Hash type "{name}" created successfully.', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error creating hash type {name}: {e}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/delete_hash_type/<int:hash_type_id>', methods=['POST'])
@login_required
def delete_hash_type(hash_type_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    hash_type = HashType.query.get_or_404(hash_type_id)
    
    # Check if hash type is used in any jobs
    from models import Job
    job_count = Job.query.filter_by(hash_type_id=hash_type_id).count()
    if job_count > 0:
        return jsonify({'error': f'Cannot delete hash type. Used in {job_count} jobs.'}), 400
    
    try:
        db.session.delete(hash_type)
        db.session.commit()
        
        flash(f'Hash type "{hash_type.name}" deleted successfully.', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting hash type {hash_type_id}: {e}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/system_info')
@login_required
def system_info():
    """Get system information"""
    try:
        from utils.system_utils import get_system_info, get_system_metrics, check_cracking_tools
        
        # Get system information
        system_info = get_system_info()
        system_metrics = get_system_metrics()
        cracking_tools = check_cracking_tools()
        
        # Get database statistics
        from models import Client, Job, Hash
        stats = {
            'total_clients': Client.query.count(),
            'connected_clients': Client.query.filter_by(status='connected').count(),
            'total_jobs': Job.query.count(),
            'running_jobs': Job.query.filter_by(status='running').count(),
            'total_hashes': Hash.query.count(),
            'cracked_hashes': Hash.query.filter_by(is_cracked=True).count()
        }
        
        return jsonify({
            'system_info': system_info,
            'system_metrics': system_metrics,
            'cracking_tools': cracking_tools,
            'database_stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/backup_database')
@login_required
def backup_database():
    """Create a database backup (placeholder)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    # This is a placeholder for database backup functionality
    # In a real implementation, you would create a backup of the SQLite database
    
    flash('Database backup functionality not yet implemented.', 'info')
    return redirect(url_for('settings.index'))

@settings_bp.route('/save_smtp', methods=['POST'])
@login_required
def save_smtp():
    if not current_user.is_admin:
        return jsonify({'error': 'Admin required'}), 403
    fields = {
        'smtp_host': ('SMTP Host', request.form.get('smtp_host', '')),
        'smtp_port': ('SMTP Port', request.form.get('smtp_port', '587')),
        'smtp_username': ('SMTP Username', request.form.get('smtp_username', '')),
        'smtp_from': ('From Address', request.form.get('smtp_from', '')),
        'smtp_tls': ('Use TLS', request.form.get('smtp_tls', 'true')),
        'notify_job_complete': ('Notify on job complete', request.form.get('notify_job_complete', 'false')),
        'notify_job_failed': ('Notify on job failed', request.form.get('notify_job_failed', 'false')),
        'notify_client_offline': ('Notify on client offline', request.form.get('notify_client_offline', 'false')),
        'notify_client_online': ('Notify on client online', request.form.get('notify_client_online', 'false')),
        'notify_email': ('Notification email', request.form.get('notify_email', '')),
    }
    # Password only updated if provided
    smtp_password = request.form.get('smtp_password', '')
    if smtp_password:
        set_setting('smtp_password', smtp_password, 'SMTP Password')

    for key, (desc, val) in fields.items():
        set_setting(key, val, desc)

    flash('Email notification settings saved.', 'success')
    return redirect(url_for('settings.index') + '#email')


@settings_bp.route('/test_email', methods=['POST'])
@login_required
def test_email():
    if not current_user.is_admin:
        return jsonify({'error': 'Admin required'}), 403
    to_addr = request.form.get('test_email_addr') or current_user.email
    try:
        from utils.notifications import send_test_email
        success, msg = send_test_email(to_addr)
        if success:
            return jsonify({'success': True, 'message': f'Test email sent to {to_addr}'})
        else:
            return jsonify({'error': msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    """Clear old job logs"""
    if not current_user.is_admin:
        return jsonify({'error': 'Admin privileges required'}), 403
    
    try:
        from models import JobLog
        from datetime import datetime, timedelta
        
        # Delete logs older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        old_logs = JobLog.query.filter(JobLog.timestamp < cutoff_date).all()
        
        count = len(old_logs)
        for log in old_logs:
            db.session.delete(log)
        
        db.session.commit()
        
        flash(f'Cleared {count} old log entries.', 'success')
        return jsonify({'success': True, 'cleared_count': count})
        
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        return jsonify({'error': str(e)}), 500
