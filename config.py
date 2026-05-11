import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///crackpi.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Upload configuration
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'txt', 'hash', 'csv'}
    
    # Cracking configuration
    WORDLISTS_DIR = '/usr/share/wordlists'
    RULES_DIR = '/usr/share/hashcat/rules'
    JOHN_PATH = '/usr/bin/john'
    HASHCAT_PATH = '/usr/bin/hashcat'
    
    # Network configuration
    NETWORK_SCAN_INTERVAL = 300  # seconds
    CLIENT_TIMEOUT = 1800  # seconds (30 minutes)
    
    # Job configuration
    MAX_CONCURRENT_JOBS = 10
    JOB_QUEUE_SIZE = 100
    
    # Default hash types
    HASH_TYPES = {
        # ── MD family ───────────────────────────────────────────────────────
        'md4':              {'hashcat_mode': 900,   'john_format': 'raw-md4'},
        'md5':              {'hashcat_mode': 0,     'john_format': 'raw-md5'},
        'md5crypt':         {'hashcat_mode': 500,   'john_format': 'md5crypt'},
        'md5-half':         {'hashcat_mode': 5100,  'john_format': 'raw-md5'},
        # ── SHA-1 ────────────────────────────────────────────────────────────
        'sha1':             {'hashcat_mode': 100,   'john_format': 'raw-sha1'},
        'sha1-linkedin':    {'hashcat_mode': 190,   'john_format': 'raw-sha1'},
        # ── SHA-2 ────────────────────────────────────────────────────────────
        'sha224':           {'hashcat_mode': 1300,  'john_format': 'raw-sha224'},
        'sha256':           {'hashcat_mode': 1400,  'john_format': 'raw-sha256'},
        'sha384':           {'hashcat_mode': 10800, 'john_format': 'raw-sha384'},
        'sha512':           {'hashcat_mode': 1700,  'john_format': 'raw-sha512'},
        'sha256crypt':      {'hashcat_mode': 7400,  'john_format': 'sha256crypt'},
        'sha512crypt':      {'hashcat_mode': 1800,  'john_format': 'sha512crypt'},
        # ── SHA-3 / Keccak ──────────────────────────────────────────────────
        'sha3-224':         {'hashcat_mode': 17300, 'john_format': 'raw-sha3-224'},
        'sha3-256':         {'hashcat_mode': 17400, 'john_format': 'raw-sha3-256'},
        'sha3-384':         {'hashcat_mode': 17500, 'john_format': 'raw-sha3-384'},
        'sha3-512':         {'hashcat_mode': 17600, 'john_format': 'raw-sha3-512'},
        'keccak-256':       {'hashcat_mode': 17800, 'john_format': 'raw-keccak-256'},
        'keccak-512':       {'hashcat_mode': 18000, 'john_format': 'raw-keccak-512'},
        # ── BLAKE2 ──────────────────────────────────────────────────────────
        'blake2b-512':      {'hashcat_mode': 600,   'john_format': 'raw-blake2'},
        # ── Windows / Active Directory ───────────────────────────────────────
        'lm':               {'hashcat_mode': 3000,  'john_format': 'lm'},
        'ntlm':             {'hashcat_mode': 1000,  'john_format': 'nt'},
        'ntlmv2':           {'hashcat_mode': 5600,  'john_format': 'netntlmv2'},
        'mscache2':         {'hashcat_mode': 2100,  'john_format': 'mscash2'},
        # ── Unix/Linux ──────────────────────────────────────────────────────
        'descrypt':         {'hashcat_mode': 1500,  'john_format': 'descrypt'},
        'bcrypt':           {'hashcat_mode': 3200,  'john_format': 'bcrypt'},
        'sha256crypt-unix': {'hashcat_mode': 7400,  'john_format': 'sha256crypt'},
        'sha512crypt-unix': {'hashcat_mode': 1800,  'john_format': 'sha512crypt'},
        'scrypt':           {'hashcat_mode': 8900,  'john_format': 'scrypt'},
        # ── PBKDF2 ──────────────────────────────────────────────────────────
        'pbkdf2-sha1':      {'hashcat_mode': 12000, 'john_format': 'pbkdf2-hmac-sha1'},
        'pbkdf2-sha256':    {'hashcat_mode': 10900, 'john_format': 'pbkdf2-hmac-sha256'},
        'pbkdf2-sha512':    {'hashcat_mode': 12100, 'john_format': 'pbkdf2-hmac-sha512'},
        # ── Argon2 ──────────────────────────────────────────────────────────
        'argon2i':          {'hashcat_mode': 13731, 'john_format': 'argon2'},
        'argon2d':          {'hashcat_mode': 13731, 'john_format': 'argon2'},
        'argon2id':         {'hashcat_mode': 13731, 'john_format': 'argon2'},
        # ── Web / Application ────────────────────────────────────────────────
        'mysql323':         {'hashcat_mode': 200,   'john_format': 'mysql'},
        'mysql41':          {'hashcat_mode': 300,   'john_format': 'mysql-sha1'},
        'mssql2000':        {'hashcat_mode': 131,   'john_format': 'mssql'},
        'mssql2005':        {'hashcat_mode': 132,   'john_format': 'mssql05'},
        'oracle11':         {'hashcat_mode': 112,   'john_format': 'oracle11'},
        'postgres-md5':     {'hashcat_mode': 11100, 'john_format': 'dynamic_1034'},
        # ── WiFi / Network ───────────────────────────────────────────────────
        'wpa-pmk':          {'hashcat_mode': 2500,  'john_format': 'wpapsk'},
        'wpa2-pmkid':       {'hashcat_mode': 22000, 'john_format': 'wpapsk'},
        # ── macOS ────────────────────────────────────────────────────────────
        'macos-sha1':       {'hashcat_mode': 122,   'john_format': 'xsha'},
        'macos-pbkdf2':     {'hashcat_mode': 7100,  'john_format': 'pbkdf2-hmac-sha512'},
        # ── Django / Python frameworks ───────────────────────────────────────
        'django-sha1':      {'hashcat_mode': 800,   'john_format': 'django'},
        'django-sha256':    {'hashcat_mode': 10000, 'john_format': 'django'},
        # ── Other ────────────────────────────────────────────────────────────
        'whirlpool':        {'hashcat_mode': 6100,  'john_format': 'whirlpool'},
        'ripemd160':        {'hashcat_mode': 6000,  'john_format': 'ripemd-160'},
        'crc32':            {'hashcat_mode': 11500, 'john_format': 'crc32'},
    }
    
    # Default wordlists
    DEFAULT_WORDLISTS = [
        '/usr/share/wordlists/rockyou.txt',
        '/usr/share/wordlists/fasttrack.txt',
        '/usr/share/wordlists/dirb/common.txt',
    ]
    
    # Default rules
    DEFAULT_RULES = [
        '/usr/share/hashcat/rules/best64.rule',
        '/usr/share/hashcat/rules/d3ad0ne.rule',
        '/usr/share/hashcat/rules/dive.rule',
    ]

class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
