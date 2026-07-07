import os
from dotenv import load_dotenv
from datetime import timedelta
import secrets

load_dotenv()

class Config:
    # Application
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    APP_NAME = os.environ.get('APP_NAME', 'ClinicConnect')
    APP_VERSION = os.environ.get('APP_VERSION', '3.0.0')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('POOL_SIZE', 5)),
        'max_overflow': int(os.environ.get('MAX_OVERFLOW', 10)),
        'pool_recycle': int(os.environ.get('POOL_RECYCLE', 3600)),
        'pool_pre_ping': True,
        'pool_timeout': int(os.environ.get('POOL_TIMEOUT', 30)),
    }
    
    # Redis - FIXED with error handling
    REDIS_URL = os.environ.get('REDIS_URL')
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    SESSION_TYPE = 'filesystem'  # Default to filesystem
    SESSION_REDIS = None
    
    # Try to use Redis if URL is available
    if REDIS_URL:
        try:
            import redis
            SESSION_REDIS = redis.from_url(
                REDIS_URL,
                password=REDIS_PASSWORD,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            SESSION_REDIS.ping()
            SESSION_TYPE = 'redis'
            print("✅ Redis connected successfully!")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            print("⚠️ Falling back to filesystem sessions")
            SESSION_TYPE = 'filesystem'
            SESSION_REDIS = None
    
    # Security
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'False') == 'True'
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or secrets.token_hex(32)
    
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    if not ENCRYPTION_KEY:
        ENCRYPTION_KEY = secrets.token_urlsafe(32)
    
    # Rate Limiting - Use memory if Redis not available
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'False') == 'True'
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100 per hour')
    if SESSION_TYPE == 'redis' and REDIS_URL:
        RATELIMIT_STORAGE_URL = REDIS_URL
    else:
        RATELIMIT_STORAGE_URL = 'memory://'
    
    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or secrets.token_hex(32)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 2592000))
    
    # Application Settings
    DEPOSIT_AMOUNT = int(os.environ.get('DEPOSIT_AMOUNT', 500))
    CONSULTATION_FEE = int(os.environ.get('CONSULTATION_FEE', 2000))
    OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES', 5))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_DURATION_MINUTES = int(os.environ.get('LOCKOUT_DURATION_MINUTES', 30))
    
    # Languages
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'en')
    SUPPORTED_LANGUAGES = os.environ.get('SUPPORTED_LANGUAGES', 'en,ur').split(',')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/clinicconnect.log')

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SESSION_TYPE = 'filesystem'  # Force filesystem for development

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = True
    RATELIMIT_ENABLED = True
    PREFERRED_URL_SCHEME = 'https'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SESSION_TYPE = 'filesystem'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}