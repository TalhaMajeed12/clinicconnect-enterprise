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

# ============================================
# SENTRY DISABLED - Commented out for development
# ============================================
# import sentry_sdk
# from sentry_sdk.integrations.flask import FlaskIntegration

db = SQLAlchemy()
mail = Mail()
migrate = Migrate()
session_manager = Session()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config.get(config_name, config['default']))
    
    # ============================================
    # SENTRY DISABLED - Commented out for development
    # ============================================
    # if os.environ.get('SENTRY_DSN'):
    #     sentry_sdk.init(
    #         dsn=os.environ.get('SENTRY_DSN'),
    #         integrations=[FlaskIntegration()],
    #         environment=config_name,
    #     )
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    
    # Redis session
    if app.config.get('REDIS_URL'):
        try:
            app.config['SESSION_REDIS'] = redis.from_url(
                app.config['REDIS_URL'],
                password=app.config.get('REDIS_PASSWORD')
            )
        except:
            pass
    session_manager.init_app(app)
    CORS(app)
    
    # Rate Limiting
    if app.config.get('RATELIMIT_ENABLED', False):
        limiter.init_app(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.clinician import clinician_bp
    from app.routes.patient import patient_bp
    from app.routes.appointments import appointments_bp
    from app.routes.payment import payment_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
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
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(429)
    def ratelimit_error(error):
        return render_template('errors/429.html'), 429