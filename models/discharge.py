from datetime import datetime
from models import db

class DischargeCoordination(db.Model):
    __tablename__ = 'discharge_coordinations'

    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('admissions.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    initiated_by_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    initiated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Clinical readiness decision by doctor
    clinical_readiness_approved = db.Column(db.Boolean, default=False, nullable=False)
    clinical_notes = db.Column(db.Text, nullable=True)
    follow_up_instructions = db.Column(db.Text, nullable=True)
    
    # Required departments flags
    requires_nursing = db.Column(db.Boolean, default=True, nullable=False)
    requires_pharmacy = db.Column(db.Boolean, default=True, nullable=False)
    requires_laboratory = db.Column(db.Boolean, default=False, nullable=False)
    requires_billing_clearance = db.Column(db.Boolean, default=True, nullable=False)

    # Clearance state
    nursing_cleared = db.Column(db.Boolean, default=False, nullable=False)
    nursing_cleared_at = db.Column(db.DateTime, nullable=True)
    nursing_cleared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    pharmacy_cleared = db.Column(db.Boolean, default=False, nullable=False)
    pharmacy_cleared_at = db.Column(db.DateTime, nullable=True)
    pharmacy_cleared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    laboratory_cleared = db.Column(db.Boolean, default=False, nullable=False)
    laboratory_cleared_at = db.Column(db.DateTime, nullable=True)
    laboratory_cleared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    billing_cleared = db.Column(db.Boolean, default=False, nullable=False)
    billing_cleared_at = db.Column(db.DateTime, nullable=True)
    billing_cleared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Readiness calculation
    is_ready_for_discharge = db.Column(db.Boolean, default=False, nullable=False)
    ready_calculated_at = db.Column(db.DateTime, nullable=True)

    # Final discharge completion
    is_finalized = db.Column(db.Boolean, default=False, nullable=False)
    final_discharged_at = db.Column(db.DateTime, nullable=True)
    final_discharged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    initiated_by_doctor = db.relationship('User', foreign_keys=[initiated_by_doctor_id])
    nursing_cleared_by = db.relationship('User', foreign_keys=[nursing_cleared_by_id])
    pharmacy_cleared_by = db.relationship('User', foreign_keys=[pharmacy_cleared_by_id])
    laboratory_cleared_by = db.relationship('User', foreign_keys=[laboratory_cleared_by_id])
    billing_cleared_by = db.relationship('User', foreign_keys=[billing_cleared_by_id])
    final_discharged_by = db.relationship('User', foreign_keys=[final_discharged_by_id])

    tasks = db.relationship('DepartmentTask', backref='discharge_coordination', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'admission_id': self.admission_id,
            'initiated_by_doctor_id': self.initiated_by_doctor_id,
            'doctor_name': self.initiated_by_doctor.full_name if self.initiated_by_doctor else None,
            'initiated_at': self.initiated_at.strftime('%Y-%m-%d %H:%M') if self.initiated_at else None,
            'clinical_readiness_approved': self.clinical_readiness_approved,
            'clinical_notes': self.clinical_notes,
            'follow_up_instructions': self.follow_up_instructions,
            'requires_nursing': self.requires_nursing,
            'requires_pharmacy': self.requires_pharmacy,
            'requires_laboratory': self.requires_laboratory,
            'requires_billing_clearance': self.requires_billing_clearance,
            'nursing_cleared': self.nursing_cleared,
            'pharmacy_cleared': self.pharmacy_cleared,
            'laboratory_cleared': self.laboratory_cleared,
            'billing_cleared': self.billing_cleared,
            'is_ready_for_discharge': self.is_ready_for_discharge,
            'is_finalized': self.is_finalized,
            'final_discharged_at': self.final_discharged_at.strftime('%Y-%m-%d %H:%M') if self.final_discharged_at else None
        }
