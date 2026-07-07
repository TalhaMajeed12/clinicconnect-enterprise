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

# Import your Flask app
from app import create_app

# Create the application instance
application = create_app('production')