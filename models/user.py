from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(30), nullable=False, index=True) # admin, doctor, nurse, pharmacy, laboratory, patient
    department = db.Column(db.String(60), nullable=True)
    employee_id = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    qualification = db.Column(db.String(120), nullable=True)
    approval_status = db.Column(db.String(20), default='approved', nullable=False) # pending, approved, rejected
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    patient_profile = db.relationship('Patient', backref='user_account', uselist=False, foreign_keys='Patient.user_id')
    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_doctor(self):
        return self.role == 'doctor'

    def is_nurse(self):
        return self.role == 'nurse'

    def is_pharmacy(self):
        return self.role == 'pharmacy'

    def is_laboratory(self):
        return self.role == 'laboratory'

    def is_patient(self):
        return self.role == 'patient'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'department': self.department,
            'employee_id': self.employee_id,
            'phone': self.phone,
            'qualification': self.qualification,
            'approval_status': self.approval_status,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }
