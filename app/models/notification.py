# NOTIFICATION
# ============================================
from datetime import datetime

from app.extensions import db

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    type = db.Column(db.String(50))
    
    title = db.Column(db.String(255))
    message = db.Column(db.Text)
    link = db.Column(db.String(255))
    
    is_read = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    read_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 
