import pytest
from datetime import datetime, date, timedelta
from models import (
    db, User, Patient, Room, Admission, DischargeCoordination,
    DepartmentTask, CommunicationLog, Notification, BillingAccount
)

def test_staff_approval_workflow(client, app, sample_data):
    """Test administrator approving a pending staff member and logging in as them."""
    # 1. Staff registers
    client.post('/register', data={
        'full_name': 'Dr. Gregory House',
        'username': 'dr_house',
        'email': 'house@hospital.test',
        'role': 'doctor',
        'department': 'Diagnostic Medicine',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })

    with app.app_context():
        user = User.query.filter_by(username='dr_house').first()
        user_id = user.id
        assert user.approval_status == 'pending'

    # 2. Login as admin and approve
    client.post('/login', data={'login_id': 'admin', 'password': 'Admin@123'})
    resp = client.post(f'/admin/staff/{user_id}/approve', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.approval_status == 'approved'

    # 3. Logout admin and login as newly approved doctor
    client.get('/logout')
    resp = client.post('/login', data={'login_id': 'dr_house', 'password': 'Password123'}, follow_redirects=True)
    assert b"Doctor Clinical Care & Discharge Overview" in resp.data

def test_patient_search_and_date_filters(client, app, sample_data):
    """Test patient list searching and filtering by keyword and admission status."""
    client.post('/login', data={'login_id': 'admin', 'password': 'Admin@123'})

    with app.app_context():
        doctor = db.session.get(User, sample_data['doctor_id'])
        nurse = db.session.get(User, sample_data['nurse_id'])
        patient = db.session.get(Patient, sample_data['patient_id'])
        room = db.session.get(Room, sample_data['room101_id'])

        adm = Admission(
            admission_number='ADM-SEARCH-01',
            patient_id=patient.id,
            room_id=room.id,
            admitting_doctor_id=doctor.id,
            assigned_nurse_id=nurse.id,
            status='Admitted',
            admission_reason='Appendicitis acute'
        )
        db.session.add(adm)
        db.session.commit()

    # Search keyword
    resp = client.get('/admin/patients?q=ADM-SEARCH-01')
    assert b"ADM-SEARCH-01" in resp.data
    assert b"John Doe" in resp.data

    # Filter status
    resp = client.get('/admin/patients?status=Admitted')
    assert b"ADM-SEARCH-01" in resp.data

    # Filter status non-matching
    resp = client.get('/admin/patients?status=Discharged')
    assert b"No patient admission records found" in resp.data

def test_communication_logs_and_notifications_persist(client, app, sample_data):
    """Test sending an interdepartmental message generates a persistent log and notification."""
    client.post('/login', data={'login_id': 'dr_test', 'password': 'Doctor@123'})

    with app.app_context():
        doctor = db.session.get(User, sample_data['doctor_id'])
        nurse = db.session.get(User, sample_data['nurse_id'])
        patient = db.session.get(Patient, sample_data['patient_id'])
        room = db.session.get(Room, sample_data['room101_id'])

        adm = Admission(
            admission_number='ADM-COMM-01',
            patient_id=patient.id,
            room_id=room.id,
            admitting_doctor_id=doctor.id,
            assigned_nurse_id=nurse.id,
            status='Admitted',
            admission_reason='Observation'
        )
        db.session.add(adm)
        db.session.commit()
        adm_id = adm.id

    # Post message targeted to Nursing
    resp = client.post('/communication/send', data={
        'admission_id': adm_id,
        'target_department': 'Nursing',
        'message': 'Please verify patient morning vitals and oxygen saturation.',
        'redirect_url': f'/doctor/patient/{adm_id}'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        comm = CommunicationLog.query.filter_by(admission_id=adm_id).first()
        assert comm is not None
        assert "morning vitals" in comm.message
        assert comm.target_department == 'Nursing'

        # Nurse should receive notification
        notif = Notification.query.filter_by(recipient_user_id=sample_data['nurse_id']).first()
        assert notif is not None
        assert "New Nursing Note" in notif.title

def test_returning_patient_preserves_admission_history(app, sample_data):
    """Test that returning patients receive new admissions while preserving earlier history."""
    with app.app_context():
        doctor = db.session.get(User, sample_data['doctor_id'])
        nurse = db.session.get(User, sample_data['nurse_id'])
        patient = db.session.get(Patient, sample_data['patient_id'])
        room1 = db.session.get(Room, sample_data['room101_id'])
        room2 = db.session.get(Room, sample_data['room102_id'])

        # Admission 1 - past
        adm1 = Admission(
            admission_number='ADM-HIST-01',
            patient_id=patient.id,
            room_id=room1.id,
            admitting_doctor_id=doctor.id,
            assigned_nurse_id=nurse.id,
            admission_date=datetime.utcnow() - timedelta(days=60),
            discharge_date=datetime.utcnow() - timedelta(days=55),
            status='Discharged',
            admission_reason='Bronchitis',
            discharge_summary='Treated with course of azithromycin. Full recovery.'
        )
        db.session.add(adm1)

        # Admission 2 - current
        adm2 = Admission(
            admission_number='ADM-HIST-02',
            patient_id=patient.id,
            room_id=room2.id,
            admitting_doctor_id=doctor.id,
            assigned_nurse_id=nurse.id,
            admission_date=datetime.utcnow() - timedelta(days=1),
            status='Admitted',
            admission_reason='Routine checkup / minor arrhythmia'
        )
        db.session.add(adm2)
        db.session.commit()

        # Check patient history
        all_admissions = patient.admissions.all()
        assert len(all_admissions) == 2
        # current_admission property should return the active non-discharged one
        assert patient.current_admission.admission_number == 'ADM-HIST-02'
