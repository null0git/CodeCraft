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
        'md5': {'hashcat_mode': 0, 'john_format': 'raw-md5'},
        'sha1': {'hashcat_mode': 100, 'john_format': 'raw-sha1'},
        'sha256': {'hashcat_mode': 1400, 'john_format': 'raw-sha256'},
        'sha512': {'hashcat_mode': 1700, 'john_format': 'raw-sha512'},
        'ntlm': {'hashcat_mode': 1000, 'john_format': 'nt'},
        'lm': {'hashcat_mode': 3000, 'john_format': 'lm'},
        'bcrypt': {'hashcat_mode': 3200, 'john_format': 'bcrypt'},
        'scrypt': {'hashcat_mode': 8900, 'john_format': 'scrypt'},
        'pbkdf2-sha1': {'hashcat_mode': 12000, 'john_format': 'pbkdf2-hmac-sha1'},
        'pbkdf2-sha256': {'hashcat_mode': 10900, 'john_format': 'pbkdf2-hmac-sha256'},
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
