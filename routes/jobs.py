from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import csv
import io
from app import db
from models import Job, Hash, HashType, Client
from utils.hash_utils import identify_hash_type, detect_hash_types_from_file
from config import Config
import logging

logger = logging.getLogger(__name__)

jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@jobs_bp.route('/')
@login_required
def index():
    # Get all jobs for current user (admins see all jobs)
    if current_user.is_admin:
        jobs = Job.query.order_by(Job.created_at.desc()).all()
    else:
        jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).all()
    
    # Calculate statistics
    pending_count = sum(1 for j in jobs if j.status == 'pending')
    running_count = sum(1 for j in jobs if j.status == 'running')
    completed_count = sum(1 for j in jobs if j.status == 'completed')
    failed_count = sum(1 for j in jobs if j.status == 'failed')
    
    return render_template('jobs.html',
                         jobs=jobs,
                         pending_count=pending_count,
                         running_count=running_count,
                         completed_count=completed_count,
                         failed_count=failed_count)

@jobs_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        try:
            # Get form data
            job_name = request.form.get('job_name')
            hash_type_name = request.form.get('hash_type')
            attack_mode = request.form.get('attack_mode', 'dictionary')
            wordlist_path = request.form.get('wordlist_path')
            rules_path = request.form.get('rules_path')
            mask = request.form.get('mask')
            priority = int(request.form.get('priority', 5))
            
            # Validate required fields
            if not job_name or not hash_type_name:
                flash('Job name and hash type are required.', 'error')
                return render_template('create_job.html', 
                                     hash_types=get_hash_types(),
                                     wordlists=get_wordlists(),
                                     rules=get_rules())
            
            # Handle file upload
            if 'hash_file' not in request.files:
                flash('Please upload a hash file.', 'error')
                return render_template('create_job.html',
                                     hash_types=get_hash_types(),
                                     wordlists=get_wordlists(),
                                     rules=get_rules())
            
            file = request.files['hash_file']
            if file.filename == '':
                flash('No file selected.', 'error')
                return render_template('create_job.html',
                                     hash_types=get_hash_types(),
                                     wordlists=get_wordlists(),
                                     rules=get_rules())
            
            # Save uploaded file
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                upload_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                
                # Create upload directory if it doesn't exist
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                
                file.save(upload_path)
                
                # Parse hash file
                hashes = parse_hash_file(upload_path)
                if not hashes:
                    flash('No valid hashes found in the uploaded file.', 'error')
                    os.remove(upload_path)
                    return render_template('create_job.html',
                                         hash_types=get_hash_types(),
                                         wordlists=get_wordlists(),
                                         rules=get_rules())
                
                # Get or create hash type
                hash_type = HashType.query.filter_by(name=hash_type_name).first()
                if not hash_type:
                    # Create new hash type if it doesn't exist
                    hash_modes = Config.HASH_TYPES.get(hash_type_name, {})
                    hash_type = HashType()
                    hash_type.name = hash_type_name
                    hash_type.hashcat_mode = hash_modes.get('hashcat_mode')
                    hash_type.john_format = hash_modes.get('john_format')
                    hash_type.description = f'Auto-created for {hash_type_name}'
                    db.session.add(hash_type)
                    db.session.flush()  # Get the ID
                
                # Create job
                job = Job()
                job.name = job_name
                job.hash_type_id = hash_type.id
                job.user_id = current_user.id
                job.status = 'pending'
                job.priority = priority
                job.total_hashes = len(hashes)
                job.attack_mode = attack_mode
                job.wordlist_path = wordlist_path
                job.rules_path = rules_path
                job.mask = mask
                
                db.session.add(job)
                db.session.flush()  # Get the job ID
                
                # Create hash records
                for hash_data in hashes:
                    hash_obj = Hash()
                    hash_obj.job_id = job.id
                    hash_obj.hash_value = hash_data['hash']
                    hash_obj.salt = hash_data.get('salt')
                    hash_obj.username = hash_data.get('username')
                    db.session.add(hash_obj)
                
                db.session.commit()
                
                # Clean up uploaded file
                os.remove(upload_path)
                
                flash(f'Job "{job_name}" created successfully with {len(hashes)} hashes.', 'success')
                return redirect(url_for('jobs.view', job_id=job.id))
            
            else:
                flash('Invalid file type. Please upload a .txt, .hash, or .csv file.', 'error')
                
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            flash(f'Error creating job: {str(e)}', 'error')
    
    return render_template('create_job.html',
                         hash_types=get_hash_types(),
                         wordlists=get_wordlists(),
                         rules=get_rules())

@jobs_bp.route('/view/<int:job_id>')
@login_required
def view(job_id):
    # Get job (check permissions)
    if current_user.is_admin:
        job = Job.query.get_or_404(job_id)
    else:
        job = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    
    # Get cracked hashes
    cracked_hashes = Hash.query.filter_by(job_id=job_id, is_cracked=True).order_by(Hash.cracked_at.desc()).all()
    
    # Get job logs
    from models import JobLog
    logs = JobLog.query.filter_by(job_id=job_id).order_by(JobLog.timestamp.desc()).limit(50).all()
    
    return render_template('view_job.html',
                         job=job,
                         cracked_hashes=cracked_hashes,
                         logs=logs)

@jobs_bp.route('/cancel/<int:job_id>', methods=['POST'])
@login_required
def cancel(job_id):
    # Get job (check permissions)
    if current_user.is_admin:
        job = Job.query.get_or_404(job_id)
    else:
        job = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    
    if job.status not in ['pending', 'running']:
        return jsonify({'error': 'Job cannot be cancelled'}), 400
    
    try:
        job.status = 'cancelled'
        job.completed_at = datetime.utcnow()
        
        # Update client status if assigned
        if job.assigned_client:
            job.assigned_client.status = 'connected'
        
        db.session.commit()
        
        # Send cancellation to client if running
        if job.assigned_client:
            # from app import socketio  # Temporarily disabled
            # socketio.emit('job_cancelled', {'job_id': job_id}, room=job.assigned_client.client_id)
            pass
        
        flash(f'Job "{job.name}" cancelled successfully.', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500

@jobs_bp.route('/download_results/<int:job_id>')
@login_required
def download_results(job_id):
    # Get job (check permissions)
    if current_user.is_admin:
        job = Job.query.get_or_404(job_id)
    else:
        job = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
    
    if job.status != 'completed':
        flash('Job must be completed to download results.', 'error')
        return redirect(url_for('jobs.view', job_id=job_id))
    
    # Get cracked hashes
    cracked_hashes = Hash.query.filter_by(job_id=job_id, is_cracked=True).all()
    
    if not cracked_hashes:
        flash('No cracked passwords found for this job.', 'info')
        return redirect(url_for('jobs.view', job_id=job_id))
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Username', 'Hash', 'Password', 'Cracked At', 'Cracked By'])
    
    # Write data
    for hash_obj in cracked_hashes:
        writer.writerow([
            hash_obj.username or '',
            hash_obj.hash_value,
            hash_obj.cracked_password,
            hash_obj.cracked_at.strftime('%Y-%m-%d %H:%M:%S') if hash_obj.cracked_at else '',
            hash_obj.cracked_by_client.hostname if hash_obj.cracked_by_client else ''
        ])
    
    # Prepare file for download
    output.seek(0)
    
    # Create a BytesIO object for send_file
    file_output = io.BytesIO()
    file_output.write(output.getvalue().encode('utf-8'))
    file_output.seek(0)
    
    filename = f"crackpi_results_{job.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        file_output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def parse_hash_file(file_path):
    """Parse hash file and return list of hash dictionaries"""
    hashes = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse different formats
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) == 2:
                        # Format: username:hash or hash:salt
                        hash_data = {
                            'hash': parts[1] if identify_hash_type(parts[1]) != 'unknown' else parts[0],
                            'username': parts[0] if identify_hash_type(parts[1]) != 'unknown' else None,
                            'salt': parts[1] if identify_hash_type(parts[0]) != 'unknown' else None
                        }
                    elif len(parts) == 3:
                        # Format: username:hash:salt
                        hash_data = {
                            'hash': parts[1],
                            'username': parts[0],
                            'salt': parts[2]
                        }
                    else:
                        # Multiple colons, treat as username:rest
                        username = parts[0]
                        rest = ':'.join(parts[1:])
                        hash_data = {
                            'hash': rest,
                            'username': username
                        }
                else:
                    # Plain hash
                    hash_data = {
                        'hash': line
                    }
                
                # Validate hash
                if identify_hash_type(hash_data['hash']) != 'unknown':
                    hashes.append(hash_data)
                else:
                    logger.warning(f"Unknown hash type on line {line_num}: {line}")
                
    except Exception as e:
        logger.error(f"Error parsing hash file {file_path}: {e}")
    
    return hashes

def get_hash_types():
    """Get available hash types"""
    return list(Config.HASH_TYPES.keys())

def get_wordlists():
    """Get available wordlists"""
    wordlists = []
    
    # Add configured wordlists
    for wordlist in Config.DEFAULT_WORDLISTS:
        if os.path.exists(wordlist):
            wordlists.append(wordlist)
    
    # Scan wordlists directory
    if os.path.exists(Config.WORDLISTS_DIR):
        for file in os.listdir(Config.WORDLISTS_DIR):
            if file.endswith(('.txt', '.lst', '.dic')):
                wordlists.append(os.path.join(Config.WORDLISTS_DIR, file))
    
    return wordlists

def get_rules():
    """Get available rule files"""
    rules = []
    
    # Add configured rules
    for rule in Config.DEFAULT_RULES:
        if os.path.exists(rule):
            rules.append(rule)
    
    # Scan rules directory
    if os.path.exists(Config.RULES_DIR):
        for file in os.listdir(Config.RULES_DIR):
            if file.endswith('.rule'):
                rules.append(os.path.join(Config.RULES_DIR, file))
    
    return rules
