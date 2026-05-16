from datetime import datetime
from app import db
from flask_login import UserMixin
from sqlalchemy import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False)
    hostname = db.Column(db.String(128))
    ip_address = db.Column(db.String(45))
    mac_address = db.Column(db.String(17))
    cpu_model = db.Column(db.String(256))
    cpu_cores = db.Column(db.Integer)
    cpu_frequency = db.Column(db.Float)
    ram_total = db.Column(db.BigInteger)
    disk_total = db.Column(db.BigInteger)
    os_info = db.Column(db.String(256))
    username = db.Column(db.String(64))
    status = db.Column(db.String(32), default='disconnected')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cpu_usage = db.Column(db.Float, default=0.0)
    ram_usage = db.Column(db.Float, default=0.0)
    disk_usage = db.Column(db.Float, default=0.0)
    network_latency = db.Column(db.Float, default=0.0)

    jobs = db.relationship('Job', backref='assigned_client', lazy=True)

class HashType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    hashcat_mode = db.Column(db.Integer)
    john_format = db.Column(db.String(32))
    description = db.Column(db.String(256))

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    hash_type_id = db.Column(db.Integer, db.ForeignKey('hash_type.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    status = db.Column(db.String(32), default='pending')
    priority = db.Column(db.Integer, default=5)

    total_hashes = db.Column(db.Integer, default=0)
    cracked_hashes = db.Column(db.Integer, default=0)
    progress_percent = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    estimated_time = db.Column(db.Integer)
    actual_time = db.Column(db.Integer)

    attack_mode = db.Column(db.String(32), default='dictionary')
    wordlist_path = db.Column(db.String(512))
    rules_path = db.Column(db.String(512))
    mask = db.Column(db.String(128))

    # ── Distributed brute-force keyspace fields ─────────────────────────────
    # charset: 'digits' | 'lowercase' | 'uppercase' | 'mixedcase' |
    #          'lowercase+digits' | 'uppercase+digits' | 'alphanumeric' |
    #          'full' | 'custom'
    charset = db.Column(db.String(32))
    charset_custom = db.Column(db.String(512))   # when charset == 'custom'
    min_length = db.Column(db.Integer)            # minimum password length
    max_length = db.Column(db.Integer)            # maximum password length

    hash_type = db.relationship('HashType', backref='jobs')
    user = db.relationship('User', backref='jobs')
    hashes = db.relationship('Hash', backref='job', lazy=True, cascade='all, delete-orphan')
    worker_assignments = db.relationship('JobWorkerAssignment', backref='job',
                                         lazy=True, cascade='all, delete-orphan')


class JobWorkerAssignment(db.Model):
    """
    Tracks which index range is assigned to each worker for a distributed
    brute-force job.  One row per (job, client) pair.

    Steps 4-9 from the keyspace spec:
      - start_index / end_index  define the non-overlapping range
      - status tracks life-cycle: assigned → running → completed | failed
      - failed ranges are automatically re-offered to idle workers
    """
    __tablename__ = 'job_worker_assignment'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)

    start_index = db.Column(db.BigInteger, nullable=False)
    end_index   = db.Column(db.BigInteger, nullable=False)

    # assigned → running → completed | failed
    status = db.Column(db.String(32), default='assigned')

    assigned_at   = db.Column(db.DateTime, default=datetime.utcnow)
    started_at    = db.Column(db.DateTime)
    completed_at  = db.Column(db.DateTime)

    passwords_tried = db.Column(db.BigInteger, default=0)

    client = db.relationship('Client', backref='worker_assignments')


class Hash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    hash_value = db.Column(db.String(512), nullable=False)
    salt = db.Column(db.String(256))
    username = db.Column(db.String(128))

    is_cracked = db.Column(db.Boolean, default=False)
    cracked_password = db.Column(db.String(256))
    cracked_at = db.Column(db.DateTime)
    cracked_by_client_id = db.Column(db.Integer, db.ForeignKey('client.id'))

    cracked_by_client = db.relationship('Client', foreign_keys=[cracked_by_client_id])

class JobLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    level = db.Column(db.String(16), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    job = db.relationship('Job', backref='logs')
    client = db.relationship('Client', backref='logs')

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(256))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
