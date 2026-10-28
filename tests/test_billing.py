import pytest
from datetime import datetime, timedelta
from models import db, Admission, Room, Patient, User, BillingAccount, BillingItem
from services.billing_service import BillingService

def test_billing_room_charges_calculation(app, sample_data):
    """Test room charges calculation based on room rate and duration."""
    with app.app_context():
        doctor = db.session.get(User, sample_data['doctor_id'])
        nurse = db.session.get(User, sample_data['nurse_id'])
        patient = db.session.get(Patient, sample_data['patient_id'])
        room = db.session.get(Room, sample_data['room101_id'])

        # 3 days stay
        adm = Admission(
            admission_number='ADM-BILL-001',
            patient_id=patient.id,
            room_id=room.id,
            admitting_doctor_id=doctor.id,
            assigned_nurse_id=nurse.id,
            admission_date=datetime.utcnow() - timedelta(days=3),
            status='Admitted',
            admission_reason='Gastritis'
        )
        db.session.add(adm)
        db.session.commit()

        account = BillingService.sync_room_charges(adm)
        assert account is not None
        # Room rate is 1200/day * 3 days = 3600
        assert account.total_room_charges == 3600.0
        assert account.total_amount > 3600.0 # Includes consultation and nursing care
        assert account.balance_due == account.total_amount

def test_add_billing_item_and_record_payment(app, sample_data):
    """Test adding medication/lab items and recording payments."""
    with app.app_context():
        doctor = db.session.get(User, sample_data['doctor_id'])
        nurse = db.session.get(User, sample_data['nurse_id'])
        patient = db.session.get(Patient, sample_data['patient_id'])
        room = db.session.get(Room, sample_data['room101_id'])
        admin = db.session.get(User, sample_data['admin_id'])

        adm = Admission(
            admission_number='ADM-BILL-002',
            patient_id=patient.id,
            room_id=room.id,
            admitting_doctor_id=doctor.id,
            assigned_nurse_id=nurse.id,
            admission_date=datetime.utcnow() - timedelta(days=1),
            status='Admitted',
            admission_reason='Migraine'
        )
        db.session.add(adm)
        db.session.commit()

        account = BillingService.sync_room_charges(adm)
        init_total = account.total_amount

        # Add Pharmacy item
        BillingService.add_billing_item(
            billing_account_id=account.id,
            category='Pharmacy',
            description='Analgesic IV Infusion',
            unit_price=250.0,
            quantity=2.0,
            added_by_user_id=admin.id
        )

        assert account.total_pharmacy_charges == 500.0
        assert account.total_amount == init_total + 500.0

        # Record payment
        payment = BillingService.record_payment(
            billing_account_id=account.id,
            amount=1000.0,
            payment_method='Credit Card',
            recorded_by_user_id=admin.id
        )

        assert payment is not None
        assert account.paid_amount == 1000.0
        assert account.balance_due == (account.total_amount - 1000.0)
        assert account.payment_status == 'Partially Paid'
