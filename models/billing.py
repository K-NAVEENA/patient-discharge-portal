from datetime import datetime
from models import db

class BillingAccount(db.Model):
    __tablename__ = 'billing_accounts'

    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('admissions.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False, index=True)
    
    total_room_charges = db.Column(db.Float, default=0.0, nullable=False)
    total_pharmacy_charges = db.Column(db.Float, default=0.0, nullable=False)
    total_lab_charges = db.Column(db.Float, default=0.0, nullable=False)
    total_consultation_charges = db.Column(db.Float, default=0.0, nullable=False)
    total_nursing_charges = db.Column(db.Float, default=0.0, nullable=False)
    total_other_charges = db.Column(db.Float, default=0.0, nullable=False)
    
    subtotal_amount = db.Column(db.Float, default=0.0, nullable=False)
    discount_amount = db.Column(db.Float, default=0.0, nullable=False)
    total_amount = db.Column(db.Float, default=0.0, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0, nullable=False)
    balance_due = db.Column(db.Float, default=0.0, nullable=False)
    
    payment_status = db.Column(db.String(30), default='Unpaid', nullable=False) # Unpaid, Partially Paid, Paid In Full
    is_finalized = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    patient = db.relationship('Patient', foreign_keys=[patient_id])
    items = db.relationship('BillingItem', backref='billing_account', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='billing_account', lazy='dynamic', cascade='all, delete-orphan')

    def recalculate_totals(self):
        items = self.items.all()
        room_tot = sum(i.total_price for i in items if i.category == 'Room')
        pharm_tot = sum(i.total_price for i in items if i.category == 'Pharmacy')
        lab_tot = sum(i.total_price for i in items if i.category == 'Laboratory')
        cons_tot = sum(i.total_price for i in items if i.category == 'Doctor Consultation')
        nurs_tot = sum(i.total_price for i in items if i.category == 'Nursing Care')
        other_tot = sum(i.total_price for i in items if i.category not in ['Room', 'Pharmacy', 'Laboratory', 'Doctor Consultation', 'Nursing Care'])

        self.total_room_charges = round(room_tot, 2)
        self.total_pharmacy_charges = round(pharm_tot, 2)
        self.total_lab_charges = round(lab_tot, 2)
        self.total_consultation_charges = round(cons_tot, 2)
        self.total_nursing_charges = round(nurs_tot, 2)
        self.total_other_charges = round(other_tot, 2)

        self.subtotal_amount = round(room_tot + pharm_tot + lab_tot + cons_tot + nurs_tot + other_tot, 2)
        self.total_amount = round(max(0.0, self.subtotal_amount - self.discount_amount), 2)

        total_paid = sum(p.amount for p in self.payments.all())
        self.paid_amount = round(total_paid, 2)
        self.balance_due = round(max(0.0, self.total_amount - self.paid_amount), 2)

        if self.balance_due <= 0.01 and self.total_amount > 0:
            self.payment_status = 'Paid In Full'
        elif self.paid_amount > 0:
            self.payment_status = 'Partially Paid'
        else:
            self.payment_status = 'Unpaid'

    def to_dict(self):
        return {
            'id': self.id,
            'admission_id': self.admission_id,
            'patient_id': self.patient_id,
            'total_room_charges': self.total_room_charges,
            'total_pharmacy_charges': self.total_pharmacy_charges,
            'total_lab_charges': self.total_lab_charges,
            'total_consultation_charges': self.total_consultation_charges,
            'total_nursing_charges': self.total_nursing_charges,
            'total_other_charges': self.total_other_charges,
            'subtotal_amount': self.subtotal_amount,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'balance_due': self.balance_due,
            'payment_status': self.payment_status,
            'is_finalized': self.is_finalized
        }


class BillingItem(db.Model):
    __tablename__ = 'billing_items'

    id = db.Column(db.Integer, primary_key=True)
    billing_account_id = db.Column(db.Integer, db.ForeignKey('billing_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False) # Room, Pharmacy, Laboratory, Doctor Consultation, Nursing Care, Other
    description = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, default=1.0, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    added_by = db.relationship('User', foreign_keys=[added_by_user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'description': self.description,
            'unit_price': self.unit_price,
            'quantity': self.quantity,
            'total_price': self.total_price,
            'added_by': self.added_by.full_name if self.added_by else 'System',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    billing_account_id = db.Column(db.Integer, db.ForeignKey('billing_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    payment_reference = db.Column(db.String(60), unique=True, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(30), nullable=False) # Cash, Credit Card, Debit Card, Insurance, UPI / Online
    transaction_id = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    recorded_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    recorded_by = db.relationship('User', foreign_keys=[recorded_by_user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'payment_reference': self.payment_reference,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'notes': self.notes,
            'recorded_by': self.recorded_by.full_name if self.recorded_by else 'System',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }
