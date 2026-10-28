from datetime import datetime
from models import db

class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    ward = db.Column(db.String(60), nullable=False) # e.g. General Ward A, ICU, Private Wing 2
    room_type = db.Column(db.String(50), nullable=False) # General Ward, Semi-Private, Private AC, ICU, Deluxe Suite
    daily_rate = db.Column(db.Float, nullable=False, default=1500.0)
    is_occupied = db.Column(db.Boolean, default=False, nullable=False)
    current_patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='SET NULL'), nullable=True)
    current_admission_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to current patient
    current_patient = db.relationship('Patient', foreign_keys=[current_patient_id])
    admissions = db.relationship('Admission', backref='room', foreign_keys='Admission.room_id', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'room_number': self.room_number,
            'ward': self.ward,
            'room_type': self.room_type,
            'daily_rate': self.daily_rate,
            'is_occupied': self.is_occupied,
            'current_patient_id': self.current_patient_id,
            'current_patient_name': self.current_patient.full_name if self.current_patient else None
        }
