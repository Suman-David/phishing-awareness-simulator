from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(50), nullable=False)
    risk_score = db.Column(db.Float, default=0.0)
    history = db.relationship('CampaignLog', backref='user', lazy=True)

class CampaignLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    campaign_name = db.Column(db.String(100))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Tracking Fields
    clicked = db.Column(db.Boolean, default=False)
    click_time = db.Column(db.DateTime, nullable=True)
    
    # Advanced Features
    reported = db.Column(db.Boolean, default=False)  # Did they report it?
    device_info = db.Column(db.String(200), default="Unknown") # Fingerprinting