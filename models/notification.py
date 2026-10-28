from datetime import datetime
from models import db

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = db.Column(db.String(60), nullable=False)
    # Event types:
    # staff_registered, staff_approved, staff_rejected,
    # patient_admitted, patient_assigned,
    # discharge_initiated, task_created, task_completed, task_blocked,
    # ready_for_discharge, discharge_finalized, patient_status_update
    
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link_url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'recipient_user_id': self.recipient_user_id,
            'event_type': self.event_type,
            'title': self.title,
            'message': self.message,
            'link_url': self.link_url,
            'is_read': self.is_read,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }
