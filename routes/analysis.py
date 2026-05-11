"""
Hash Analysis and Reporting Routes
Advanced analysis of hash files with entropy, pattern detection, and statistics
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from models import Job, Hash, HashType, Client
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func
import math
import io
import csv
import logging

logger = logging.getLogger(__name__)
analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')


def shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string"""
    if not data:
        return 0.0
    frequency = {}
    for c in data:
        frequency[c] = frequency.get(c, 0) + 1
    entropy = 0.0
    length = len(data)
    for count in frequency.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def classify_hash_length(length: int) -> str:
    length_map = {
        8: 'CRC32 / MySQL 3.x',
        16: 'MD5 Half / MySQL 3.x',
        32: 'MD5 / NTLM / MD4',
        40: 'SHA-1 / RIPEMD-160',
        48: 'SHA-224 / Tiger-192',
        56: 'SHA-224',
        64: 'SHA-256 / Keccak-256 / Blake2s',
        80: 'RIPEMD-320',
        96: 'SHA-384',
        128: 'SHA-512 / Keccak-512 / Blake2b',
        56: 'DES-crypt (incl prefix)',
    }
    return length_map.get(length, f'Unknown ({length} chars)')


def detect_charset(hash_val: str) -> str:
    has_upper = any(c.isupper() for c in hash_val)
    has_lower = any(c.islower() for c in hash_val)
    has_digit = any(c.isdigit() for c in hash_val)
    has_special = any(not c.isalnum() for c in hash_val)

    if set(hash_val) <= set('0123456789abcdefABCDEF'):
        return 'hexadecimal'
    elif set(hash_val) <= set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='):
        return 'base64'
    elif has_special:
        return 'mixed+special'
    elif has_upper and has_lower and has_digit:
        return 'alphanumeric-mixed'
    elif (has_upper or has_lower) and has_digit:
        return 'alphanumeric'
    elif has_digit and not has_upper and not has_lower:
        return 'numeric'
    else:
        return 'alphabetic'


@analysis_bp.route('/')
@login_required
def index():
    """Main analysis dashboard"""
    # Global statistics
    total_jobs = Job.query.filter_by(user_id=current_user.id).count() if not current_user.is_admin else Job.query.count()
    total_hashes = db.session.query(func.count(Hash.id)).join(Job).filter(
        Job.user_id == current_user.id if not current_user.is_admin else True
    ).scalar() or 0

    cracked_count = db.session.query(func.count(Hash.id)).join(Job).filter(
        Hash.is_cracked == True,
        Job.user_id == current_user.id if not current_user.is_admin else True
    ).scalar() or 0

    crack_rate = round((cracked_count / total_hashes * 100), 1) if total_hashes > 0 else 0

    # Jobs for job selector
    if current_user.is_admin:
        jobs = Job.query.order_by(Job.created_at.desc()).all()
    else:
        jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).all()

    # Hash type distribution across all jobs
    ht_dist = db.session.query(HashType.name, func.count(Job.id)).join(
        Job, Job.hash_type_id == HashType.id
    ).group_by(HashType.name).all()

    # Status distribution
    status_dist = db.session.query(Job.status, func.count(Job.id)).group_by(Job.status).all()

    # Cracking activity over last 7 days
    daily_cracks = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.session.query(func.count(Hash.id)).filter(
            Hash.is_cracked == True,
            Hash.cracked_at >= day_start,
            Hash.cracked_at < day_end
        ).scalar() or 0
        daily_cracks.append({'date': day_start.strftime('%b %d'), 'count': count})

    # Top cracked jobs
    top_jobs = db.session.query(
        Job.name, Job.total_hashes, Job.cracked_hashes, Job.status
    ).order_by(Job.cracked_hashes.desc()).limit(5).all()

    return render_template('analysis.html',
        total_jobs=total_jobs,
        total_hashes=total_hashes,
        cracked_count=cracked_count,
        crack_rate=crack_rate,
        jobs=jobs,
        hash_type_dist=[{'name': r[0], 'count': r[1]} for r in ht_dist],
        status_dist=[{'status': r[0], 'count': r[1]} for r in status_dist],
        daily_cracks=daily_cracks,
        top_jobs=[{'name': r[0], 'total': r[1], 'cracked': r[2], 'status': r[3]} for r in top_jobs]
    )


@analysis_bp.route('/job/<int:job_id>')
@login_required
def job_analysis(job_id):
    """Detailed analysis of a specific job"""
    if current_user.is_admin:
        job = Job.query.get_or_404(job_id)
    else:
        job = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()

    hashes = Hash.query.filter_by(job_id=job_id).all()
    cracked = [h for h in hashes if h.is_cracked]
    uncracked = [h for h in hashes if not h.is_cracked]

    # Length distribution
    length_dist = {}
    for h in hashes:
        ln = len(h.hash_value)
        length_dist[ln] = length_dist.get(ln, 0) + 1

    # Entropy analysis
    entropies = [shannon_entropy(h.hash_value) for h in hashes]
    avg_entropy = round(sum(entropies) / len(entropies), 3) if entropies else 0
    min_entropy = round(min(entropies), 3) if entropies else 0
    max_entropy = round(max(entropies), 3) if entropies else 0

    # Charset distribution
    charset_dist = {}
    for h in hashes:
        cs = detect_charset(h.hash_value)
        charset_dist[cs] = charset_dist.get(cs, 0) + 1

    # Duplicate detection
    seen = {}
    for h in hashes:
        seen[h.hash_value.lower()] = seen.get(h.hash_value.lower(), 0) + 1
    duplicates = sum(1 for c in seen.values() if c > 1)

    # Cracked password analysis
    pw_lengths = {}
    pw_charsets = {}
    for h in cracked:
        if h.cracked_password:
            ln = len(h.cracked_password)
            pw_lengths[ln] = pw_lengths.get(ln, 0) + 1
            cs = 'numeric' if h.cracked_password.isdigit() else (
                'alpha' if h.cracked_password.isalpha() else (
                    'alphanumeric' if h.cracked_password.isalnum() else 'complex'
                )
            )
            pw_charsets[cs] = pw_charsets.get(cs, 0) + 1

    # Time to crack (if available)
    crack_times = []
    for h in cracked:
        if h.cracked_at and job.started_at:
            delta = (h.cracked_at - job.started_at).total_seconds()
            if delta >= 0:
                crack_times.append(delta)
    avg_crack_time = round(sum(crack_times) / len(crack_times), 1) if crack_times else None

    # Brute-force estimator
    estimator = build_crack_estimator(job.hash_type.name if job.hash_type else 'md5')

    return render_template('analysis_job.html',
        job=job,
        hashes=hashes,
        cracked=cracked,
        uncracked=uncracked,
        length_dist=sorted(length_dist.items()),
        avg_entropy=avg_entropy,
        min_entropy=min_entropy,
        max_entropy=max_entropy,
        charset_dist=list(charset_dist.items()),
        duplicates=duplicates,
        pw_lengths=sorted(pw_lengths.items()),
        pw_charsets=list(pw_charsets.items()),
        avg_crack_time=avg_crack_time,
        estimator=estimator
    )


@analysis_bp.route('/api/job/<int:job_id>/stats')
@login_required
def job_stats_api(job_id):
    """JSON API for job statistics"""
    if current_user.is_admin:
        job = Job.query.get_or_404(job_id)
    else:
        job = Job.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()

    hashes = Hash.query.filter_by(job_id=job_id).all()
    cracked = [h for h in hashes if h.is_cracked]

    length_dist = {}
    entropy_buckets = {'low (0-2)': 0, 'medium (2-3.5)': 0, 'high (3.5+)': 0}
    charset_dist = {}

    for h in hashes:
        ln = len(h.hash_value)
        length_dist[str(ln)] = length_dist.get(str(ln), 0) + 1
        e = shannon_entropy(h.hash_value)
        if e < 2:
            entropy_buckets['low (0-2)'] += 1
        elif e < 3.5:
            entropy_buckets['medium (2-3.5)'] += 1
        else:
            entropy_buckets['high (3.5+)'] += 1
        cs = detect_charset(h.hash_value)
        charset_dist[cs] = charset_dist.get(cs, 0) + 1

    pw_lengths = {}
    for h in cracked:
        if h.cracked_password:
            ln = str(len(h.cracked_password))
            pw_lengths[ln] = pw_lengths.get(ln, 0) + 1

    return jsonify({
        'job_id': job_id,
        'job_name': job.name,
        'total_hashes': len(hashes),
        'cracked': len(cracked),
        'crack_rate': round(len(cracked) / len(hashes) * 100, 1) if hashes else 0,
        'length_dist': length_dist,
        'entropy_buckets': entropy_buckets,
        'charset_dist': charset_dist,
        'pw_length_dist': pw_lengths,
    })


@analysis_bp.route('/export/csv')
@login_required
def export_global_csv():
    """Export global analysis as CSV"""
    if current_user.is_admin:
        jobs = Job.query.all()
    else:
        jobs = Job.query.filter_by(user_id=current_user.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Job Name', 'Hash Type', 'Status', 'Total Hashes', 'Cracked', 'Crack Rate %',
                     'Created', 'Completed', 'Duration (s)'])
    for job in jobs:
        duration = None
        if job.started_at and job.completed_at:
            duration = int((job.completed_at - job.started_at).total_seconds())
        crack_rate = round((job.cracked_hashes / job.total_hashes * 100), 1) if job.total_hashes > 0 else 0
        writer.writerow([
            job.name,
            job.hash_type.name if job.hash_type else 'Unknown',
            job.status,
            job.total_hashes,
            job.cracked_hashes,
            crack_rate,
            job.created_at.strftime('%Y-%m-%d %H:%M') if job.created_at else '',
            job.completed_at.strftime('%Y-%m-%d %H:%M') if job.completed_at else '',
            duration or ''
        ])

    output.seek(0)
    buf = io.BytesIO(output.getvalue().encode('utf-8'))
    buf.seek(0)
    filename = f"crackpi_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(buf, mimetype='text/csv', as_attachment=True, download_name=filename)


def build_crack_estimator(hash_type: str) -> dict:
    """Build brute-force time estimation for common hardware"""
    # Approximate hashes/second for each algorithm on typical hardware
    speeds = {
        'md5':    {'cpu': 500_000_000,   'gpu_mid': 10_000_000_000,  'gpu_high': 50_000_000_000},
        'sha1':   {'cpu': 200_000_000,   'gpu_mid':  4_000_000_000,  'gpu_high': 20_000_000_000},
        'sha256': {'cpu':  80_000_000,   'gpu_mid':  1_500_000_000,  'gpu_high':  8_000_000_000},
        'sha512': {'cpu':  25_000_000,   'gpu_mid':    600_000_000,  'gpu_high':  3_000_000_000},
        'ntlm':   {'cpu': 800_000_000,   'gpu_mid': 15_000_000_000,  'gpu_high': 70_000_000_000},
        'bcrypt': {'cpu':       5_000,   'gpu_mid':       100_000,   'gpu_high':      500_000},
        'argon2': {'cpu':         200,   'gpu_mid':         2_000,   'gpu_high':       10_000},
    }
    ht_lower = hash_type.lower().replace('-', '').replace('_', '')
    speed = None
    for key, val in speeds.items():
        if key in ht_lower or ht_lower.startswith(key):
            speed = val
            break
    if not speed:
        speed = speeds['sha256']

    def format_time(seconds):
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            return f"{seconds/60:.1f} minutes"
        elif seconds < 86400:
            return f"{seconds/3600:.1f} hours"
        elif seconds < 86400 * 365:
            return f"{seconds/86400:.1f} days"
        else:
            return f"{seconds/86400/365:.1f} years"

    charsets = {
        'digits (10)':        {'size': 10,  'lengths': [6, 8, 10]},
        'lowercase (26)':     {'size': 26,  'lengths': [6, 8, 10]},
        'alphanumeric (62)':  {'size': 62,  'lengths': [6, 8, 10]},
        'full ASCII (95)':    {'size': 95,  'lengths': [6, 8, 10]},
    }

    results = {}
    for cs_name, cs_data in charsets.items():
        cs_results = {}
        for length in cs_data['lengths']:
            keyspace = cs_data['size'] ** length
            cs_results[f'{length} chars'] = {
                hw: format_time(keyspace / spd)
                for hw, spd in speed.items()
            }
        results[cs_name] = cs_results

    return {
        'hash_type': hash_type,
        'speeds': {hw: f"{spd:,} H/s" for hw, spd in speed.items()},
        'estimates': results
    }
