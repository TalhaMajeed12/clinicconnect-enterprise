from flask import Flask, render_template, session
from flask_session import Session
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import os
from logging.handlers import RotatingFileHandler
from app.config import config
import redis
import traceback

from app.extensions import (
    db,
    mail,
    migrate,
    limiter,
    login_manager,
    csrf
)

session_manager = Session()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # Load configuration
    app.config.from_object(config.get(config_name, config['default']))

    if config_name == 'production':
        missing = [name for name in ('DATABASE_URL', 'SECRET_KEY', 'ENCRYPTION_KEY', 'JWT_SECRET_KEY')
                   if not os.environ.get(name)]
        if missing:
            raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")
    
    # Initialize extensions once.
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)


    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import redirect, url_for
        if session.get('role') == 'admin':
            return redirect(url_for('auth.admin_login'))
        if session.get('role') == 'clinician':
            return redirect(url_for('auth.clinician_login'))
        return redirect(url_for('auth.login'))

    csrf.init_app(app)

    # Configure server-side sessions. Redis is optional on free deployments.
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
            app.config['SESSION_TYPE'] = 'redis'
            app.logger.info('Redis connected successfully')
        except Exception as e:
            app.logger.warning(
                'Redis connection failed; using filesystem sessions: %s', e
            )
            app.config['SESSION_TYPE'] = 'filesystem'
            app.config['SESSION_REDIS'] = None
    else:
        app.config['SESSION_TYPE'] = 'filesystem'
    
    session_manager.init_app(app)
    CORS(app, resources={
        r'/api/*': {
            'origins': app.config.get('CORS_ALLOWED_ORIGINS', []),
            'supports_credentials': False,
        }
    })
    
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
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.clinician import clinician_bp
    from app.routes.patient import patient_bp
    from app.routes.appointments import appointments_bp
    from app.routes.payment import payment_bp
    from app.routes.api import api_bp
    csrf.exempt(api_bp)
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(clinician_bp, url_prefix='/clinician')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(appointments_bp, url_prefix='/appointments')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Error handlers
    register_error_handlers(app)
    
    # ============================================
    # UNIVERSAL CACHE PREVENTION & SECURITY HEADERS
    # ============================================
    @app.after_request
    def add_security_and_cache_headers(response):
        # Security headers
        if app.config.get('SESSION_COOKIE_SECURE', False):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=(), payment=()'
        )
        response.headers['Content-Security-Policy'] = '; '.join([
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'self'",
            "form-action 'self'",
            "img-src 'self' data:",
            "connect-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com",
            "font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com",
        ])
        
        # Cache prevention - UNIVERSAL FIX
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
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
        logging.getLogger(__name__).warning('File logging setup failed: %s', e)

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
