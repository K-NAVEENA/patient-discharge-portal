from datetime import datetime
from models import db

class Admission(db.Model):
    __tablename__ = 'admissions'

    id = db.Column(db.Integer, primary_key=True)
    admission_number = db.Column(db.String(30), unique=True, nullable=False, index=True) # ADM-2026-0001
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    admitting_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    admission_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    discharge_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(40), default='Admitted', nullable=False, index=True)
    # Status values:
    # 'Admitted'
    # 'Discharge In Progress'
    # 'Awaiting Departmental Clearance'
    # 'Ready for Final Discharge'
    # 'Discharged'

    admission_reason = db.Column(db.Text, nullable=False)
    initial_diagnosis = db.Column(db.Text, nullable=True)
    admission_remarks = db.Column(db.Text, nullable=True)
    discharged_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    discharge_summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    admitting_doctor = db.relationship('User', foreign_keys=[admitting_doctor_id])
    assigned_nurse = db.relationship('User', foreign_keys=[assigned_nurse_id])
    discharged_by = db.relationship('User', foreign_keys=[discharged_by_user_id])
    
    discharge_coordination = db.relationship('DischargeCoordination', backref='admission', uselist=False, cascade='all, delete-orphan')
    tasks = db.relationship('DepartmentTask', backref='admission', lazy='dynamic', cascade='all, delete-orphan')
    billing_account = db.relationship('BillingAccount', backref='admission', uselist=False, cascade='all, delete-orphan')
    communication_logs = db.relationship('CommunicationLog', backref='admission', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def length_of_stay_days(self):
        end_time = self.discharge_date or datetime.utcnow()
        delta = end_time - self.admission_date
        days = delta.days
        # If less than 1 day or has fractional hours, count minimum 1 day or calculate
        fractional_day = delta.seconds / 86400.0
        calculated = days + (1 if fractional_day > 0.05 else 0)
        return max(1, calculated)

    def to_dict(self):
        return {
            'id': self.id,
            'admission_number': self.admission_number,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else None,
            'room_id': self.room_id,
            'room_number': self.room.room_number if self.room else None,
            'admitting_doctor_id': self.admitting_doctor_id,
            'doctor_name': self.admitting_doctor.full_name if self.admitting_doctor else None,
            'assigned_nurse_id': self.assigned_nurse_id,
            'nurse_name': self.assigned_nurse.full_name if self.assigned_nurse else None,
            'admission_date': self.admission_date.strftime('%Y-%m-%d %H:%M') if self.admission_date else None,
            'discharge_date': self.discharge_date.strftime('%Y-%m-%d %H:%M') if self.discharge_date else None,
            'status': self.status,
            'admission_reason': self.admission_reason,
            'initial_diagnosis': self.initial_diagnosis,
            'length_of_stay_days': self.length_of_stay_days
        }
