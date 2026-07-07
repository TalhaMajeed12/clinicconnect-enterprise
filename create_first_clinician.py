 
from app import create_app, db
from app.models import User, ClinicianProfile

app = create_app('development')

with app.app_context():
    print("\n🔐 Create Admin Account")
    print("-" * 30)
    
    username = input('Username: ').strip()
    
    if User.query.filter_by(username=username).first():
        print('❌ Username already exists.')
        exit()
    
    password = input('Password: ').strip()
    full_name = input('Full Name: ').strip()
    email = input('Email: ').strip()
    phone = input('Phone: ').strip()
    specialty = input('Specialty: ').strip()
    
    user = User(
        username=username,
        role='admin'
    )
    user.full_name = full_name
    user.email = email
    user.phone = phone
    user.set_password(password)
    
    db.session.add(user)
    db.session.flush()
    
    clinician = ClinicianProfile(
        user_id=user.id,
        specialty=specialty,
        consultation_fee=2000,
        is_available=True
    )
    db.session.add(clinician)
    db.session.commit()
    
    print(f"\n✅ Admin '{full_name}' created successfully!")
    print(f"   Username: {username}")
    print(f"   Role: Admin")