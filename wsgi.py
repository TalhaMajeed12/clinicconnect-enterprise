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
from app.models import User, PatientProfile, ClinicianProfile, Appointment, Payment, AuditLog

# Create the application instance
application = create_app('production')

# Auto-create database tables if they don't exist
with application.app_context():
    db.create_all()
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
        db.session.commit()
        print("✅ Admin user created (username: admin, password: admin123)")
    
    # Check if admin has a clinician profile (to prevent it showing in clinicians list)
    admin_clinician = ClinicianProfile.query.filter_by(user_id=admin.id).first()
    if not admin_clinician:
        # Create a clinician profile for admin (but we'll filter it out)
        admin_clinician = ClinicianProfile(
            user_id=admin.id,
            specialty='Administration',
            consultation_fee=0
        )
        db.session.add(admin_clinician)
        db.session.commit()
        print("✅ Admin clinician profile created")