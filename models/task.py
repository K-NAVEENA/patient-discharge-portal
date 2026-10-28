from datetime import datetime
from models import db

class DepartmentTask(db.Model):
    __tablename__ = 'department_tasks'

    id = db.Column(db.Integer, primary_key=True)
    task_code = db.Column(db.String(30), unique=True, nullable=False, index=True) # e.g. TSK-1001
    admission_id = db.Column(db.Integer, db.ForeignKey('admissions.id', ondelete='CASCADE'), nullable=False, index=True)
    discharge_coordination_id = db.Column(db.Integer, db.ForeignKey('discharge_coordinations.id', ondelete='CASCADE'), nullable=False, index=True)
    department = db.Column(db.String(40), nullable=False, index=True) # Nursing, Pharmacy, Laboratory, Billing
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='Pending', nullable=False, index=True) # Pending, In Progress, Completed, Blocked
    blocked_reason = db.Column(db.Text, nullable=True)
    
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    completed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_user_id])
    completed_by = db.relationship('User', foreign_keys=[completed_by_user_id])
    communication_logs = db.relationship('CommunicationLog', backref='task', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'task_code': self.task_code,
            'admission_id': self.admission_id,
            'discharge_coordination_id': self.discharge_coordination_id,
            'department': self.department,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'blocked_reason': self.blocked_reason,
            'assigned_to_user_id': self.assigned_to_user_id,
            'assigned_to_name': self.assigned_to.full_name if self.assigned_to else None,
            'completed_by_user_id': self.completed_by_user_id,
            'completed_by_name': self.completed_by.full_name if self.completed_by else None,
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M') if self.completed_at else None,
            'remarks': self.remarks,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }
