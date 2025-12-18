from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta

db = SQLAlchemy()

def get_local_time():
    """Restituisce l'ora locale italiana (UTC+1)"""
    return datetime.now(timezone.utc) + timedelta(hours=1)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=get_local_time)
    
    vm_requests = db.relationship('VMRequest', foreign_keys='VMRequest.user_id', backref='user', lazy=True)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

class VMRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vm_type = db.Column(db.String(20), nullable=False)  
    vm_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  
    
    # Dettagli VM dopo la creazione
    vm_id = db.Column(db.Integer, nullable=True)
    hostname = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    username = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(255), nullable=True)
    ssh_key = db.Column(db.Text, nullable=True)
    
    # Approvazione/Rifiuto
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=get_local_time)
    updated_at = db.Column(db.DateTime, default=get_local_time, onupdate=get_local_time)
    
    def get_status_badge_class(self):
        status_classes = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'failed': 'danger' 
        }
        return status_classes.get(self.status, 'secondary')
    
    def get_status_display(self):
        """Restituisce il testo da mostrare per lo status"""
        if self.status == 'rejected' and self.error_message:
            return 'Rifiutata (Fallita)'
        status_names = {
            'pending': 'In Attesa',
            'approved': 'Approvata',
            'rejected': 'Rifiutata',
            'failed': 'Fallita'
        }
        return status_names.get(self.status, self.status.capitalize())
    
    def get_vm_type_display(self):
        type_names = {
            'bronze': 'Bronze',
            'silver': 'Silver',
            'gold': 'Gold'
        }
        return type_names.get(self.vm_type, self.vm_type.capitalize())
