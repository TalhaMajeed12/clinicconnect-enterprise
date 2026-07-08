# ============================================
# CLINICONNECT WSGI CONFIGURATION
# ============================================

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/TalhaMajeed/clinicconnect-enterprise'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

# Import your Flask app and db
from app import create_app, db

# Create the application instance
application = create_app('production')

# Auto-create database tables if they don't exist
with application.app_context():
    db.create_all()
    print("✅ Database tables verified/created successfully")