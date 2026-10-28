import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import datetime, date, timedelta
from app import create_app
from models import db, User, Room, Patient, Admission, DischargeCoordination, DepartmentTask, BillingAccount

class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-secret-key-1234'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    DEFAULT_ROOM_RATES = {
        'General Ward': 1200.0,
        'Semi-Private': 2500.0,
        'Private AC': 4500.0,
        'ICU': 8500.0,
        'Deluxe Suite': 6000.0
    }
    CONSULTATION_CHARGE_PER_DAY = 750.0
    NURSING_CARE_CHARGE_PER_DAY = 500.0

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def sample_data(app):
    with app.app_context():
        # Admin
        admin = User(
            username='admin',
            email='admin@hospital.test',
            full_name='Test Admin',
            role='admin',
            approval_status='approved',
            is_active=True
        )
        admin.set_password('Admin@123')

        # Doctor
        doctor = User(
            username='dr_test',
            email='dr.test@hospital.test',
            full_name='Dr. Test Physician',
            role='doctor',
            department='Cardiology',
            approval_status='approved',
            is_active=True
        )
        doctor.set_password('Doctor@123')

        # Nurse
        nurse = User(
            username='nurse_test',
            email='nurse.test@hospital.test',
            full_name='Test Nurse',
            role='nurse',
            department='Nursing',
            approval_status='approved',
            is_active=True
        )
        nurse.set_password('Nurse@123')

        # Pharmacy
        pharm = User(
            username='pharm_test',
            email='pharm.test@hospital.test',
            full_name='Test Pharmacist',
            role='pharmacy',
            department='Pharmacy',
            approval_status='approved',
            is_active=True
        )
        pharm.set_password('Pharm@123')

        # Laboratory
        lab = User(
            username='lab_test',
            email='lab.test@hospital.test',
            full_name='Test Lab Tech',
            role='laboratory',
            department='Laboratory',
            approval_status='approved',
            is_active=True
        )
        lab.set_password('Lab@123')

        db.session.add_all([admin, doctor, nurse, pharm, lab])
        db.session.flush()

        # Room
        room101 = Room(
            room_number='101',
            ward='General Ward A',
            room_type='General Ward',
            daily_rate=1200.0,
            is_occupied=False
        )
        room102 = Room(
            room_number='102',
            ward='General Ward A',
            room_type='General Ward',
            daily_rate=1200.0,
            is_occupied=False
        )
        db.session.add_all([room101, room102])
        db.session.flush()

        # Patient & Portal Account
        pat_user = User(
            username='pat_test',
            email='pat.test@hospital.test',
            full_name='John Doe',
            role='patient',
            approval_status='approved',
            is_active=True
        )
        pat_user.set_password('Patient@123')
        db.session.add(pat_user)
        db.session.flush()

        patient = Patient(
            patient_id='PID-2026-9001',
            full_name='John Doe',
            date_of_birth=date(1985, 5, 20),
            gender='Male',
            phone='555-1111',
            email='pat.test@hospital.test',
            user_id=pat_user.id
        )
        db.session.add(patient)
        db.session.flush()

        data_ids = {
            'admin_id': admin.id,
            'doctor_id': doctor.id,
            'nurse_id': nurse.id,
            'pharmacy_id': pharm.id,
            'laboratory_id': lab.id,
            'patient_user_id': pat_user.id,
            'patient_id': patient.id,
            'room101_id': room101.id,
            'room102_id': room102.id,
        }
        db.session.commit()
        return data_ids
