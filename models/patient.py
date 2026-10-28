from datetime import datetime, date
from models import db

class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(30), unique=True, nullable=False, index=True) # e.g. PID-2026-0001
    full_name = db.Column(db.String(120), nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False) # Male, Female, Other
    blood_group = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact_name = db.Column(db.String(120), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    admissions = db.relationship('Admission', backref='patient', lazy='dynamic', order_by='desc(Admission.admission_date)')
    communication_logs = db.relationship('CommunicationLog', backref='patient', lazy='dynamic')

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def current_admission(self):
        # Returns active admission if not discharged
        return self.admissions.filter(Admission.status != 'Discharged').first()

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'full_name': self.full_name,
            'age': self.age,
            'date_of_birth': self.date_of_birth.strftime('%Y-%m-%d') if self.date_of_birth else None,
            'gender': self.gender,
            'blood_group': self.blood_group,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'has_portal_account': bool(self.user_id),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }

from models.admission import Admission  # imported for current_admission query
