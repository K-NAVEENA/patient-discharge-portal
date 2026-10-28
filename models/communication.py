from datetime import datetime
from models import db

class CommunicationLog(db.Model):
    __tablename__ = 'communication_logs'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('admissions.id', ondelete='CASCADE'), nullable=False, index=True)
    discharge_coordination_id = db.Column(db.Integer, db.ForeignKey('discharge_coordinations.id', ondelete='SET NULL'), nullable=True)
    task_id = db.Column(db.Integer, db.ForeignKey('department_tasks.id', ondelete='SET NULL'), nullable=True)
    
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_role = db.Column(db.String(30), nullable=False)
    source_department = db.Column(db.String(50), nullable=False)
    target_department = db.Column(db.String(50), nullable=False) # e.g. All Staff, Nursing, Pharmacy, Laboratory, Doctor, Admin
    
    message = db.Column(db.Text, nullable=False)
    log_type = db.Column(db.String(30), default='message', nullable=False) # message, status_change, alert, clearance
    
    is_acknowledged = db.Column(db.Boolean, default=False, nullable=False)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id])
    acknowledged_by = db.relationship('User', foreign_keys=[acknowledged_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'admission_id': self.admission_id,
            'discharge_coordination_id': self.discharge_coordination_id,
            'task_id': self.task_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.full_name if self.sender else 'System',
            'sender_role': self.sender_role,
            'source_department': self.source_department,
            'target_department': self.target_department,
            'message': self.message,
            'log_type': self.log_type,
            'is_acknowledged': self.is_acknowledged,
            'acknowledged_by_name': self.acknowledged_by.full_name if self.acknowledged_by else None,
            'acknowledged_at': self.acknowledged_at.strftime('%Y-%m-%d %H:%M') if self.acknowledged_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }
