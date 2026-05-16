from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import Client, Job, Hash, JobLog, HashType, JobWorkerAssignment
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

ONLINE_STATUSES = ('online', 'connected', 'idle', 'working')


# ── Health check ──────────────────────────────────────────────────────────────

@api_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        'status': 'ok',
        'message': 'CrackPi server is running',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0'
    })


# ── Client registration & lifecycle ──────────────────────────────────────────

@api_bp.route('/clients/register', methods=['POST'])
def register_client():
    data = request.get_json(silent=True) or {}
    client_id = data.get('client_id')
    system_info = data.get('system_info', {})

    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        client = Client()
        client.client_id  = client_id
        client.hostname   = system_info.get('network', {}).get('hostname', 'Unknown')
        client.ip_address = system_info.get('network', {}).get('ip_address', '127.0.0.1')
        client.mac_address= system_info.get('network', {}).get('mac_address', '00:00:00:00:00:00')
        client.cpu_cores  = system_info.get('cpu', {}).get('cores', 1)
        client.ram_total  = system_info.get('memory', {}).get('total', 0)
        client.disk_total = system_info.get('disk', {}).get('total', 0)
        db.session.add(client)
        logger.info(f"Registered new client: {client_id}")
    else:
        logger.info(f"Reconnected client: {client_id}")

    client.status    = 'online'
    client.last_seen = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'registered', 'client_id': client_id})


@api_bp.route('/clients/disconnect', methods=['POST'])
def client_disconnect():
    data = request.get_json(silent=True) or {}
    client_id = data.get('client_id')
    if client_id:
        client = Client.query.filter_by(client_id=client_id).first()
        if client:
            client.status    = 'offline'
            client.last_seen = datetime.utcnow()
            # Mark their open worker assignments as failed → ranges re-queued
            _fail_client_assignments(client)
            db.session.commit()
            logger.info(f"Client disconnected gracefully: {client_id}")
    return jsonify({'status': 'ok'})


# ── Heartbeat — the coordinator core ─────────────────────────────────────────

@api_bp.route('/clients/heartbeat', methods=['POST'])
def client_heartbeat():
    """
    Central coordinator heartbeat.

    For idle clients:
      1. Check for a pending distributed (bruteforce + keyspace) job and
         spread it across ALL currently idle workers at once (Steps 4-5).
      2. If a worker already has an 'assigned' range waiting, dispatch it
         (handles clients that were idle when distribution happened).
      3. If a failed range from a crashed worker is available, reassign it
         to this worker (Step 9 — failure recovery).
      4. Fall back to single-worker dictionary/hybrid dispatch.

    For working clients:
      - If their active job is no longer 'running' (completed/cancelled/failed),
        send a stop_job command so they halt immediately (Step 8).
    """
    data = request.get_json(silent=True) or {}
    client_id = data.get('client_id')

    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    reported_status = data.get('status', 'online')
    client.status = reported_status if reported_status in ('working', 'online', 'idle') else 'online'
    client.last_seen = datetime.utcnow()

    metrics = data.get('system_metrics', {})
    if metrics:
        client.cpu_usage       = metrics.get('cpu_usage', 0)
        client.ram_usage       = metrics.get('memory_usage', 0)
        client.disk_usage      = metrics.get('disk_usage', 0)
        client.network_latency = metrics.get('network_latency', 0)

    commands = []

    # ── Working client: check if their job has ended elsewhere ───────────────
    if client.status == 'working':
        current_job_id = data.get('current_job')
        if current_job_id:
            active_job = Job.query.get(current_job_id)
            if active_job and active_job.status not in ('running',):
                commands.append({'command': 'stop_job', 'job_id': current_job_id,
                                 'reason': f'Job status is {active_job.status}'})
                client.status = 'online'

    # ── Idle client: look for work ────────────────────────────────────────────
    if client.status in ('online', 'idle'):

        # Priority 1: does this client already have an assigned range waiting?
        my_assignment = (
            JobWorkerAssignment.query
            .filter_by(client_id=client.id, status='assigned')
            .join(Job)
            .filter(Job.status == 'running')
            .first()
        )
        if my_assignment:
            cmd = _build_bruteforce_command(my_assignment)
            if cmd:
                my_assignment.status    = 'running'
                my_assignment.started_at = datetime.utcnow()
                client.status           = 'working'
                commands.append(cmd)

        # Priority 2: pick up a failed/abandoned range from another worker
        if not commands:
            orphan = (
                JobWorkerAssignment.query
                .filter_by(status='failed')
                .join(Job)
                .filter(Job.status == 'running')
                .order_by(JobWorkerAssignment.id.asc())
                .first()
            )
            if orphan:
                orphan.client_id  = client.id
                orphan.status     = 'running'
                orphan.started_at = datetime.utcnow()
                client.status     = 'working'
                cmd = _build_bruteforce_command(orphan)
                if cmd:
                    commands.append(cmd)
                    _log(orphan.job_id, client.id,
                         f"Reassigned failed range [{orphan.start_index}–{orphan.end_index}] "
                         f"to {client.hostname or client_id} (Step 9: failure recovery)")

        # Priority 3: new pending brute-force job → distribute across ALL idle workers
        if not commands:
            pending_bf = (
                Job.query
                .filter(
                    Job.status == 'pending',
                    Job.attack_mode == 'bruteforce',
                    Job.charset.isnot(None),
                )
                .order_by(Job.priority.asc(), Job.created_at.asc())
                .first()
            )
            if pending_bf:
                _distribute_bruteforce_job(pending_bf)   # creates all assignments
                db.session.flush()
                # Now pick up this client's fresh assignment
                my_assignment = JobWorkerAssignment.query.filter_by(
                    job_id=pending_bf.id, client_id=client.id, status='assigned'
                ).first()
                if my_assignment:
                    my_assignment.status     = 'running'
                    my_assignment.started_at = datetime.utcnow()
                    client.status            = 'working'
                    commands.append(_build_bruteforce_command(my_assignment))

        # Priority 4: fall back to single-worker dictionary / hybrid job
        if not commands:
            pending_dict = (
                Job.query
                .filter(
                    Job.status == 'pending',
                    Job.client_id.is_(None),
                    db.or_(
                        Job.attack_mode != 'bruteforce',
                        Job.charset.is_(None),
                    )
                )
                .order_by(Job.priority.asc(), Job.created_at.asc())
                .first()
            )
            if pending_dict:
                pending_dict.client_id  = client.id
                pending_dict.status     = 'running'
                pending_dict.started_at = datetime.utcnow()
                client.status           = 'working'

                hashes       = Hash.query.filter_by(job_id=pending_dict.id, is_cracked=False).all()
                hash_type_rec = HashType.query.get(pending_dict.hash_type_id)
                commands.append({
                    'command':       'start_job',
                    'job_id':        pending_dict.id,
                    'job_name':      pending_dict.name,
                    'hash_type':     hash_type_rec.name if hash_type_rec else 'unknown',
                    'attack_mode':   pending_dict.attack_mode,
                    'wordlist_path': pending_dict.wordlist_path,
                    'rules_path':    pending_dict.rules_path,
                    'mask':          pending_dict.mask,
                    'hashes': [
                        {'id': h.id, 'hash': h.hash_value, 'salt': h.salt, 'username': h.username}
                        for h in hashes
                    ],
                })
                _log(pending_dict.id, client.id,
                     f"Job dispatched to {client.hostname or client_id}")

    db.session.commit()
    return jsonify({'status': 'ok', 'commands': commands})


# ── Job status / progress / password-found ────────────────────────────────────

@api_bp.route('/jobs/<int:job_id>/status', methods=['POST'])
def update_job_status(job_id):
    data = request.get_json(silent=True) or {}
    job  = Job.query.get_or_404(job_id)

    new_status = data.get('status')
    if new_status in ('completed', 'failed', 'cancelled', 'running'):
        job.status = new_status
        if new_status in ('completed', 'failed', 'cancelled'):
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.actual_time = int((job.completed_at - job.started_at).total_seconds())
            # Mark all worker assignments as completed/failed accordingly
            asgn_status = 'completed' if new_status == 'completed' else 'failed'
            JobWorkerAssignment.query.filter_by(
                job_id=job.id, status='running'
            ).update({'status': asgn_status})
            # Free up the client
            if job.assigned_client:
                job.assigned_client.status = 'online'

    details = data.get('details', {})
    if details.get('message'):
        _log(job.id, None, details['message'], details.get('level', 'info'))

    # Update the specific worker assignment status
    client_id_str = data.get('client_id')
    if client_id_str and new_status in ('completed', 'failed', 'cancelled'):
        client = Client.query.filter_by(client_id=client_id_str).first()
        if client:
            JobWorkerAssignment.query.filter_by(
                job_id=job.id, client_id=client.id, status='running'
            ).update({'status': asgn_status if new_status != 'running' else 'running',
                      'completed_at': datetime.utcnow()})

    # Check if all assignments are done → mark job complete
    if job.attack_mode == 'bruteforce' and job.status == 'running':
        remaining = JobWorkerAssignment.query.filter_by(
            job_id=job.id, status='running'
        ).count()
        assigned = JobWorkerAssignment.query.filter_by(
            job_id=job.id, status='assigned'
        ).count()
        if remaining == 0 and assigned == 0:
            job.status       = 'completed'
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.actual_time = int((job.completed_at - job.started_at).total_seconds())

    db.session.commit()

    # Email notifications
    try:
        from utils.notifications import notify_job_completed, notify_job_failed
        from models import Settings
        def _gs(k, d=''):
            s = Settings.query.filter_by(key=k).first()
            return s.value if s else d
        if new_status == 'completed' and _gs('notify_job_complete', 'false') == 'true':
            to = _gs('notify_email') or (job.user.email if job.user else None)
            if to:
                notify_job_completed(job, job.cracked_hashes, job.total_hashes, to)
        elif new_status == 'failed' and _gs('notify_job_failed', 'false') == 'true':
            to = _gs('notify_email') or (job.user.email if job.user else None)
            if to:
                notify_job_failed(job, details.get('message', 'Unknown error'), to)
    except Exception as e:
        logger.debug(f"Email notification error: {e}")

    return jsonify({'status': 'ok'})


@api_bp.route('/jobs/<int:job_id>/progress', methods=['POST'])
def update_job_progress(job_id):
    data = request.get_json(silent=True) or {}
    job  = Job.query.get_or_404(job_id)

    progress = data.get('progress_percent')
    if progress is not None:
        job.progress_percent = float(progress)

    cracked_count = Hash.query.filter_by(job_id=job_id, is_cracked=True).count()
    job.cracked_hashes = cracked_count
    if job.total_hashes and job.total_hashes > 0:
        job.progress_percent = (cracked_count / job.total_hashes) * 100

    # Update passwords_tried on the worker's assignment
    client_id_str = data.get('client_id')
    attempts      = data.get('attempts', 0)
    if client_id_str and attempts:
        client = Client.query.filter_by(client_id=client_id_str).first()
        if client:
            JobWorkerAssignment.query.filter_by(
                job_id=job.id, client_id=client.id, status='running'
            ).update({'passwords_tried': attempts})

    db.session.commit()
    return jsonify({'status': 'ok'})


@api_bp.route('/jobs/<int:job_id>/password-found', methods=['POST'])
def password_found(job_id):
    """
    Step 8 — Success Detection:
    Record the cracked password; if all hashes are done, mark job completed
    and signal all other workers to stop.
    """
    data = request.get_json(silent=True) or {}
    job  = Job.query.get_or_404(job_id)

    hash_value    = (data.get('hash_value') or '').strip()
    password      = (data.get('password')   or '').strip()
    client_id_str = data.get('client_id')

    if not hash_value or not password:
        return jsonify({'error': 'hash_value and password are required'}), 400

    hash_obj = Hash.query.filter_by(job_id=job_id, hash_value=hash_value).first()
    if hash_obj and not hash_obj.is_cracked:
        hash_obj.is_cracked        = True
        hash_obj.cracked_password  = password
        hash_obj.cracked_at        = datetime.utcnow()

        if client_id_str:
            cracking_client = Client.query.filter_by(client_id=client_id_str).first()
            if cracking_client:
                hash_obj.cracked_by_client_id = cracking_client.id

        cracked_count = Hash.query.filter_by(job_id=job_id, is_cracked=True).count() + 1
        job.cracked_hashes = cracked_count
        if job.total_hashes and job.total_hashes > 0:
            job.progress_percent = (cracked_count / job.total_hashes) * 100

        _log(job.id, None,
             f"Password cracked: {hash_value[:16]}... → {password}", 'info')

        # If all hashes cracked → complete the job and stop all workers
        if cracked_count >= (job.total_hashes or 1):
            job.status       = 'completed'
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.actual_time = int((job.completed_at - job.started_at).total_seconds())
            # Mark all running assignments done — heartbeat will send stop_job
            JobWorkerAssignment.query.filter_by(
                job_id=job.id
            ).filter(
                JobWorkerAssignment.status.in_(('running', 'assigned'))
            ).update({'status': 'completed', 'completed_at': datetime.utcnow()})
            _log(job.id, None,
                 f"All {cracked_count} hashes cracked — stopping all workers", 'info')

        db.session.commit()
        return jsonify({'status': 'ok', 'cracked': True})

    return jsonify({'status': 'ok', 'cracked': False,
                    'note': 'Hash already cracked or not found'})


# ── Worker assignment status ──────────────────────────────────────────────────

@api_bp.route('/jobs/<int:job_id>/range-complete', methods=['POST'])
def range_complete(job_id):
    """Worker finished its assigned range without finding the password."""
    data = request.get_json(silent=True) or {}
    client_id_str = data.get('client_id')
    assignment_id = data.get('assignment_id')

    if client_id_str:
        client = Client.query.filter_by(client_id=client_id_str).first()
        if client:
            q = JobWorkerAssignment.query.filter_by(job_id=job_id, client_id=client.id)
            if assignment_id:
                q = q.filter_by(id=assignment_id)
            q.filter(JobWorkerAssignment.status == 'running').update({
                'status': 'completed',
                'completed_at': datetime.utcnow(),
                'passwords_tried': data.get('attempts', 0),
            })
            client.status = 'online'

    # Check if ALL assignments are done → job complete
    job = Job.query.get_or_404(job_id)
    if job.status == 'running':
        still_active = JobWorkerAssignment.query.filter(
            JobWorkerAssignment.job_id == job.id,
            JobWorkerAssignment.status.in_(('assigned', 'running'))
        ).count()
        if still_active == 0:
            job.status       = 'completed'
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.actual_time = int((job.completed_at - job.started_at).total_seconds())
            _log(job.id, None,
                 "All workers finished their ranges — keyspace exhausted", 'info')

    db.session.commit()
    return jsonify({'status': 'ok'})


@api_bp.route('/jobs/<int:job_id>/keyspace', methods=['GET'])
@login_required
def job_keyspace(job_id):
    """Return keyspace info and worker assignments for a job."""
    job = Job.query.get_or_404(job_id)
    if job.attack_mode != 'bruteforce' or not job.charset:
        return jsonify({'distributed': False})

    from utils.keyspace import resolve_charset, keyspace_summary
    charset = resolve_charset(job.charset, job.charset_custom or '')
    summary = keyspace_summary(charset, job.min_length or 1, job.max_length or 8)

    assignments = JobWorkerAssignment.query.filter_by(job_id=job.id).all()
    workers = []
    for a in assignments:
        workers.append({
            'assignment_id': a.id,
            'client_id':     a.client.client_id if a.client else None,
            'hostname':      a.client.hostname  if a.client else 'Unknown',
            'start_index':   a.start_index,
            'end_index':     a.end_index,
            'range_size':    a.end_index - a.start_index + 1,
            'passwords_tried': a.passwords_tried,
            'status':        a.status,
            'assigned_at':   a.assigned_at.isoformat() if a.assigned_at else None,
        })

    return jsonify({
        'distributed': True,
        'charset':     job.charset,
        'charset_size': len(charset),
        'min_length':  job.min_length,
        'max_length':  job.max_length,
        'keyspace':    summary,
        'workers':     workers,
    })


# ── Timeout check ─────────────────────────────────────────────────────────────

@api_bp.route('/clients/timeout_check', methods=['POST'])
@login_required
def timeout_check():
    timeout_minutes = int((request.get_json(silent=True) or {}).get('timeout_minutes', 5))
    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)

    stale = Client.query.filter(
        Client.last_seen < cutoff,
        Client.status.in_(ONLINE_STATUSES)
    ).all()

    timed_out = []
    for c in stale:
        _fail_client_assignments(c)
        running = Job.query.filter_by(client_id=c.id, status='running').all()
        for job in running:
            # Only fail single-worker jobs; distributed jobs continue via other workers
            if job.attack_mode != 'bruteforce' or not job.charset:
                job.status       = 'failed'
                job.completed_at = datetime.utcnow()
                _log(job.id, c.id, 'Client timed out — job marked failed', 'error')
        c.status = 'offline'
        timed_out.append(c.client_id)

        try:
            from utils.notifications import notify_client_offline
            from models import Settings
            def _gs(k, d=''):
                s = Settings.query.filter_by(key=k).first()
                return s.value if s else d
            if _gs('notify_client_offline', 'false') == 'true':
                to = _gs('notify_email')
                if to:
                    notify_client_offline(c, to)
        except Exception:
            pass

    db.session.commit()
    return jsonify({'timed_out': timed_out, 'count': len(timed_out)})


# ── API stats / clients list ──────────────────────────────────────────────────

@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    from models import Job, Hash, Client
    online = Client.query.filter(Client.status.in_(ONLINE_STATUSES)).count()
    return jsonify({
        'total_clients':  Client.query.count(),
        'online_clients': online,
        'total_jobs':     Job.query.count(),
        'running_jobs':   Job.query.filter_by(status='running').count(),
        'pending_jobs':   Job.query.filter_by(status='pending').count(),
        'total_hashes':   Hash.query.count(),
        'cracked_hashes': Hash.query.filter_by(is_cracked=True).count(),
    })


@api_bp.route('/clients')
@login_required
def get_clients():
    clients = Client.query.all()
    return jsonify({
        'clients': [{
            'id':          c.id,
            'client_id':   c.client_id,
            'hostname':    c.hostname,
            'ip_address':  c.ip_address,
            'status':      c.status,
            'last_seen':   c.last_seen.isoformat() if c.last_seen else None,
            'cpu_usage':   c.cpu_usage,
            'ram_usage':   c.ram_usage,
            'disk_usage':  c.disk_usage,
        } for c in clients]
    })


@api_bp.route('/clients/<client_id>/jobs', methods=['GET'])
def get_client_jobs(client_id):
    client = Client.query.filter_by(client_id=client_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    jobs = Job.query.filter_by(client_id=client.id, status='running').all()
    job_data = []
    for job in jobs:
        hashes        = Hash.query.filter_by(job_id=job.id, is_cracked=False).all()
        hash_type_rec = HashType.query.get(job.hash_type_id)
        job_data.append({
            'job_id':       job.id,
            'job_name':     job.name,
            'hash_type':    hash_type_rec.name if hash_type_rec else 'unknown',
            'attack_mode':  job.attack_mode,
            'wordlist_path': job.wordlist_path,
            'rules_path':   job.rules_path,
            'mask':         job.mask,
            'hashes': [{'id': h.id, 'hash': h.hash_value, 'salt': h.salt, 'username': h.username}
                       for h in hashes],
        })
    return jsonify({'jobs': job_data})


# ── Private helpers ───────────────────────────────────────────────────────────

def _log(job_id, client_id, message, level='info'):
    entry = JobLog()
    entry.job_id    = job_id
    entry.client_id = client_id
    entry.level     = level
    entry.message   = message
    db.session.add(entry)


def _fail_client_assignments(client: Client):
    """Mark all open assignments for a client as failed so ranges are re-queued."""
    JobWorkerAssignment.query.filter(
        JobWorkerAssignment.client_id == client.id,
        JobWorkerAssignment.status.in_(('assigned', 'running'))
    ).update({'status': 'failed', 'completed_at': datetime.utcnow()})


def _build_bruteforce_command(assignment: JobWorkerAssignment) -> dict | None:
    """Build the start_job command dict for a distributed bruteforce assignment."""
    job = assignment.job
    if not job or not job.charset:
        return None

    try:
        from utils.keyspace import resolve_charset
        charset_str = resolve_charset(job.charset, job.charset_custom or '')
    except Exception as e:
        logger.error(f"Keyspace charset error: {e}")
        return None

    hashes        = Hash.query.filter_by(job_id=job.id, is_cracked=False).all()
    hash_type_rec = HashType.query.get(job.hash_type_id)

    return {
        'command':       'start_job',
        'job_id':        job.id,
        'job_name':      job.name,
        'hash_type':     hash_type_rec.name if hash_type_rec else 'unknown',
        'attack_mode':   'bruteforce',
        # Keyspace parameters (Steps 2 & 6)
        'charset':       charset_str,
        'charset_name':  job.charset,
        'min_length':    job.min_length or 1,
        'max_length':    job.max_length or 8,
        'start_index':   assignment.start_index,
        'end_index':     assignment.end_index,
        'assignment_id': assignment.id,
        'hashes': [
            {'id': h.id, 'hash': h.hash_value, 'salt': h.salt, 'username': h.username}
            for h in hashes
        ],
    }


def _distribute_bruteforce_job(job: Job):
    """
    Steps 4-5: Divide the keyspace among all currently idle workers.
    Creates one JobWorkerAssignment per idle worker with non-overlapping
    index ranges. Marks the job as 'running'.
    """
    from utils.keyspace import resolve_charset, total_keyspace, divide_keyspace

    try:
        charset_str = resolve_charset(job.charset, job.charset_custom or '')
    except Exception as e:
        logger.error(f"Cannot distribute job {job.id}: {e}")
        return

    min_len = job.min_length or 1
    max_len = job.max_length or 8
    total   = total_keyspace(charset_str, min_len, max_len)

    idle_workers = Client.query.filter(
        Client.status.in_(('online', 'idle'))
    ).all()

    n = max(1, len(idle_workers))
    ranges = divide_keyspace(total, n)

    for worker, (start, end) in zip(idle_workers, ranges):
        a             = JobWorkerAssignment()
        a.job_id      = job.id
        a.client_id   = worker.id
        a.start_index = start
        a.end_index   = end
        a.status      = 'assigned'
        db.session.add(a)

    job.status     = 'running'
    job.started_at = datetime.utcnow()

    _log(job.id, None,
         f"Keyspace distributed: {total:,} combinations across {n} worker(s). "
         f"Charset='{job.charset}' ({len(charset_str)} chars), "
         f"lengths {min_len}–{max_len}.",
         'info')
