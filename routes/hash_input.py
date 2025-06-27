from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
import logging
from app import db
from models import Job, Hash, HashType, Client
from utils.hash_cracker import HashCracker, RangeDistributor, PasswordGenerator
from config import Config

logger = logging.getLogger(__name__)

hash_input_bp = Blueprint('hash_input', __name__, url_prefix='/hash')

@hash_input_bp.route('/')
@login_required
def index():
    """Hash input page with enhanced range distribution"""
    # Get available clients for distribution preview
    connected_clients = Client.query.filter_by(status='connected').all()
    
    return render_template('hash_input.html', 
                         connected_clients=connected_clients,
                         charset_options=get_charset_options())

@hash_input_bp.route('/create', methods=['POST'])
@login_required
def create_job():
    """Create a new distributed cracking job"""
    try:
        # Get form data
        job_name = request.form.get('job_name', '').strip()
        hash_input = request.form.get('hash_input', '').strip()
        attack_mode = request.form.get('attack_mode', 'range')
        
        # Validate required fields
        if not job_name or not hash_input:
            flash('Job name and hash are required.', 'error')
            return redirect(url_for('hash_input.index'))
        
        # Parse and validate hashes
        hashes = parse_hash_input(hash_input)
        if not hashes:
            flash('No valid hashes found in input.', 'error')
            return redirect(url_for('hash_input.index'))
        
        # Detect hash type for first hash
        hash_type_name = HashCracker.detect_hash_type(hashes[0]['hash'])
        if hash_type_name == 'unknown':
            hash_type_name = request.form.get('hash_type_manual', 'md5')
        
        # Get or create hash type
        hash_type = HashType.query.filter_by(name=hash_type_name).first()
        if not hash_type:
            hash_type = HashType()
            hash_type.name = hash_type_name
            hash_type.description = f'Auto-detected: {hash_type_name}'
            db.session.add(hash_type)
            db.session.flush()
        
        # Get connected clients
        connected_clients = Client.query.filter_by(status='connected').all()
        if not connected_clients:
            flash('No connected clients available for job distribution.', 'error')
            return redirect(url_for('hash_input.index'))
        
        # Calculate range distribution based on attack mode
        if attack_mode == 'range':
            distribution_result = calculate_range_distribution(request.form, len(connected_clients))
        elif attack_mode == 'charset':
            distribution_result = calculate_charset_distribution(request.form, len(connected_clients))
        else:
            flash('Invalid attack mode selected.', 'error')
            return redirect(url_for('hash_input.index'))
        
        if 'error' in distribution_result:
            flash(distribution_result['error'], 'error')
            return redirect(url_for('hash_input.index'))
        
        # Create main job
        job = Job()
        job.name = job_name
        job.hash_type_id = hash_type.id
        job.user_id = current_user.id
        job.status = 'pending'
        job.priority = int(request.form.get('priority', 5))
        job.total_hashes = len(hashes)
        job.attack_mode = attack_mode
        job.created_at = datetime.utcnow()
        
        # Store distribution parameters
        job.wordlist_path = distribution_result.get('charset', '')
        job.mask = distribution_result.get('pattern', '')
        
        db.session.add(job)
        db.session.flush()
        
        # Create hash records
        for hash_data in hashes:
            hash_obj = Hash()
            hash_obj.job_id = job.id
            hash_obj.hash_value = hash_data['hash']
            hash_obj.salt = hash_data.get('salt')
            hash_obj.username = hash_data.get('username')
            db.session.add(hash_obj)
        
        # Assign ranges to clients
        client_assignments = distribution_result['client_ranges']
        for i, client in enumerate(connected_clients[:len(client_assignments)]):
            client_range = client_assignments[i]
            client.status = 'assigned'
            
            # Store assignment details (you might want to create a separate table for this)
            # For now, we'll use the existing job assignment
            if i == 0:  # Assign job to first client as primary
                job.client_id = client.id
        
        db.session.commit()
        
        flash(f'Job "{job_name}" created and distributed among {len(client_assignments)} clients.', 'success')
        return redirect(url_for('jobs.view', job_id=job.id))
        
    except Exception as e:
        logger.error(f"Error creating hash job: {e}")
        flash(f'Error creating job: {str(e)}', 'error')
        return redirect(url_for('hash_input.index'))

@hash_input_bp.route('/preview-distribution', methods=['POST'])
@login_required
def preview_distribution():
    """Preview how ranges will be distributed among clients"""
    try:
        attack_mode = request.json.get('attack_mode')
        connected_clients = Client.query.filter_by(status='connected').count()
        
        if connected_clients == 0:
            return jsonify({'error': 'No connected clients available'})
        
        if attack_mode == 'range':
            result = calculate_range_distribution(request.json, connected_clients)
        elif attack_mode == 'charset':
            result = calculate_charset_distribution(request.json, connected_clients)
        else:
            return jsonify({'error': 'Invalid attack mode'})
        
        if 'error' in result:
            return jsonify({'error': result['error']})
        
        return jsonify({
            'success': True,
            'total_combinations': result['total_combinations'],
            'client_ranges': result['client_ranges'],
            'num_clients': connected_clients
        })
        
    except Exception as e:
        logger.error(f"Error previewing distribution: {e}")
        return jsonify({'error': str(e)})

def parse_hash_input(hash_input: str) -> list:
    """Parse hash input and return list of hash dictionaries"""
    hashes = []
    lines = hash_input.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Support different formats:
        # hash
        # username:hash
        # hash:salt
        # username:hash:salt
        
        parts = line.split(':')
        
        if len(parts) == 1:
            # Just hash
            hashes.append({
                'hash': parts[0].strip(),
                'username': None,
                'salt': None
            })
        elif len(parts) == 2:
            # Could be username:hash or hash:salt
            # Try to detect based on hash length
            if HashCracker.detect_hash_type(parts[1]) != 'unknown':
                # username:hash
                hashes.append({
                    'hash': parts[1].strip(),
                    'username': parts[0].strip(),
                    'salt': None
                })
            else:
                # hash:salt
                hashes.append({
                    'hash': parts[0].strip(),
                    'username': None,
                    'salt': parts[1].strip()
                })
        elif len(parts) == 3:
            # username:hash:salt
            hashes.append({
                'hash': parts[1].strip(),
                'username': parts[0].strip(),
                'salt': parts[2].strip()
            })
    
    return hashes

def calculate_range_distribution(form_data: dict, num_clients: int) -> dict:
    """Calculate distribution for custom range attack"""
    try:
        start_range = form_data.get('start_range', '').strip()
        end_range = form_data.get('end_range', '').strip()
        charset = form_data.get('charset', 'digits')
        
        if not start_range or not end_range:
            return {'error': 'Start and end range are required'}
        
        if len(start_range) != len(end_range):
            return {'error': 'Start and end range must have the same length'}
        
        # Get actual charset
        charset = PasswordGenerator.get_charset_by_name(charset)
        
        # Calculate total combinations
        total_combinations = RangeDistributor.calculate_range_combinations(
            start_range, end_range, charset
        )
        
        # Distribute among clients
        client_ranges = RangeDistributor.distribute_custom_range(
            start_range, end_range, charset, num_clients
        )
        
        return {
            'total_combinations': total_combinations,
            'client_ranges': client_ranges,
            'charset': charset,
            'pattern': f'{start_range}-{end_range}'
        }
        
    except Exception as e:
        return {'error': str(e)}

def calculate_charset_distribution(form_data: dict, num_clients: int) -> dict:
    """Calculate distribution for charset-based attack"""
    try:
        charset = form_data.get('charset', 'digits')
        length = int(form_data.get('password_length', 4))
        
        if length <= 0 or length > 20:
            return {'error': 'Password length must be between 1 and 20'}
        
        # Get actual charset
        charset = PasswordGenerator.get_charset_by_name(charset)
        
        # Calculate total combinations
        total_combinations = RangeDistributor.calculate_total_combinations(charset, length)
        
        if total_combinations > 10**12:  # Limit to prevent excessive computation
            return {'error': 'Too many combinations. Please reduce length or charset size.'}
        
        # Distribute among clients
        client_ranges = RangeDistributor.distribute_charset_range(
            charset, length, num_clients
        )
        
        return {
            'total_combinations': total_combinations,
            'client_ranges': client_ranges,
            'charset': charset,
            'pattern': f'length-{length}'
        }
        
    except Exception as e:
        return {'error': str(e)}

def get_charset_options():
    """Get available charset options for the UI"""
    return [
        {'value': 'digits', 'label': 'Digits (0-9)', 'example': '0123456789'},
        {'value': 'lowercase', 'label': 'Lowercase Letters (a-z)', 'example': 'abcdefghijklmnopqrstuvwxyz'},
        {'value': 'uppercase', 'label': 'Uppercase Letters (A-Z)', 'example': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'},
        {'value': 'letters', 'label': 'All Letters (a-z, A-Z)', 'example': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'},
        {'value': 'alphanumeric', 'label': 'Letters + Digits', 'example': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'},
        {'value': 'symbols', 'label': 'Symbols', 'example': '!@#$%^&*()_+-=[]{}|;:,.<>?'},
        {'value': 'all', 'label': 'All Characters', 'example': 'Letters + Digits + Symbols'},
    ]