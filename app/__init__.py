from flask import Flask, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from flask_cors import CORS
import logging
import os
from logging.handlers import RotatingFileHandler
from config import config
import redis
import traceback

db = SQLAlchemy()
mail = Mail()
migrate = Migrate()
session_manager = Session()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config.get(config_name, config['default']))
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    
    # Redis session - with better error handling
    if app.config.get('REDIS_URL'):
        try:
            app.config['SESSION_REDIS'] = redis.from_url(
                app.config['REDIS_URL'],
                password=app.config.get('REDIS_PASSWORD'),
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            app.config['SESSION_REDIS'].ping()
            print("✅ Redis connected successfully!")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            print("⚠️ Falling back to filesystem sessions")
            app.config['SESSION_TYPE'] = 'filesystem'
            app.config['SESSION_REDIS'] = None
    else:
        app.config['SESSION_TYPE'] = 'filesystem'
    
    session_manager.init_app(app)
    CORS(app)
    
    # Rate Limiting - use memory if Redis not available
    if app.config.get('RATELIMIT_ENABLED', False):
        if not app.config.get('SESSION_REDIS'):
            app.config['RATELIMIT_STORAGE_URL'] = 'memory://'
        limiter.init_app(app)
    
    # ============================================
    # ADD TRANSLATION FUNCTION TO JINJA2 TEMPLATES
    # ============================================
    from app.utils.translations import t
    app.jinja_env.globals.update(t=t)
    
    # Also add as context processor for templates
    @app.context_processor
    def inject_translations():
        from app.utils.translations import t
        return dict(t=t)
    
    # Setup logging
    setup_logging(app)
    
    # ============================================
    # REGISTER BLUEPRINTS
    # ============================================
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp      # ← ADD THIS
    from app.routes.admin import admin_bp
    from app.routes.clinician import clinician_bp
    from app.routes.patient import patient_bp
    from app.routes.appointments import appointments_bp
    from app.routes.payment import payment_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)           # ← ADD THIS
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(clinician_bp, url_prefix='/clinician')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(appointments_bp, url_prefix='/appointments')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Error handlers
    register_error_handlers(app)
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        if app.config.get('SESSION_COOKIE_SECURE', False):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    # Language middleware
    @app.before_request
    def set_language():
        lang = session.get('language')
        if not lang:
            session['language'] = app.config.get('DEFAULT_LANGUAGE', 'en')
    
    # ============================================
    # CREATE DATABASE TABLES ON STARTUP
    # ============================================
    with app.app_context():
        try:
            # Import all models to ensure they're registered
            from app.models import (
                User, PatientProfile, ClinicianProfile, 
                Appointment, Payment, AuditLog, 
                Visit, Prescription, Attendance,
                OtpVerification, LoginAttempt, SystemSetting
            )
            
            # Create all tables
            db.create_all()
            app.logger.info("✅ Database tables verified/created successfully")
            print("✅ Database tables verified/created successfully")
            
            # Create admin user if it doesn't exist
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    role='admin',
                    full_name='System Administrator',
                    email='admin@clinicconnect.com',
                    phone='1234567890'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.flush()
                app.logger.info("✅ Admin user created")
                print("✅ Admin user created")
                
                # Create admin clinician profile
                admin_clinician = ClinicianProfile.query.filter_by(user_id=admin.id).first()
                if not admin_clinician:
                    admin_clinician = ClinicianProfile(
                        user_id=admin.id,
                        specialty='Administration',
                        consultation_fee=0
                    )
                    db.session.add(admin_clinician)
                    app.logger.info("✅ Admin clinician profile created")
                    print("✅ Admin clinician profile created")
                
                db.session.commit()
                app.logger.info("✅ Admin setup complete (username: admin, password: admin123)")
                print("✅ Admin setup complete (username: admin, password: admin123)")
            
        except Exception as e:
            app.logger.error(f"❌ Database initialization error: {str(e)}")
            app.logger.error(traceback.format_exc())
            print(f"❌ Database initialization error: {str(e)}")
            print(traceback.format_exc())
    
    return app

def setup_logging(app):
    try:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', 'logs/clinicconnect.log'),
            maxBytes=10485760,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info(f'{app.config["APP_NAME"]} v{app.config["APP_VERSION"]} started')
    except Exception as e:
        print(f"⚠️ Logging setup warning: {e}")

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        app.logger.error(traceback.format_exc())
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(429)
    def ratelimit_error(error):
        return render_template('errors/429.html'), 429