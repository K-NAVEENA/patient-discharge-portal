import pytest
from datetime import datetime, date
from models import db, Admission, Room, Patient, DischargeCoordination, DepartmentTask, User
from services.discharge_service import DischargeService
from services.billing_service import BillingService

def test_patient_admission_and_room_allocation(client, app, sample_data):
    """Test admitting a patient, allocating room, and ensuring occupancy is marked."""
    # Login as admin
    client.post('/login', data={'login_id': 'admin', 'password': 'Admin@123'})

    resp = client.post('/admin/patients/admit', data={
        'full_name': 'Alice Smith',
        'date_of_birth': '1990-01-15',
        'gender': 'Female',
        'blood_group': 'A+',
        'phone': '555-4321',
        'email': 'alice@example.test',
        'address': '123 Test St',
        'room_id': sample_data['room101_id'],
        'doctor_id': sample_data['doctor_id'],
        'nurse_id': sample_data['nurse_id'],
        'admission_reason': 'Post-operative recovery',
        'create_portal_account': 'on',
        'temp_password': 'Hospital@123'
    }, follow_redirects=True)

    assert resp.status_code == 200
    with app.app_context():
        room = db.session.get(Room, sample_data['room101_id'])
        assert room.is_occupied is True
        adm = Admission.query.filter_by(room_id=room.id, status='Admitted').first()
        assert adm is not None
        assert adm.patient.full_name == 'Alice Smith'

def test_double_room_occupancy_prevented(client, app, sample_data):
    """Test that an occupied room cannot be allocated to another patient."""
    client.post('/login', data={'login_id': 'admin', 'password': 'Admin@123'})

    # First admission into room 102
    client.post('/admin/patients/admit', data={
        'full_name': 'Patient One',
        'date_of_birth': '1992-02-02',
        'gender': 'Male',
        'phone': '555-0001',
        'room_id': sample_data['room102_id'],
        'doctor_id': sample_data['doctor_id'],
        'nurse_id': sample_data['nurse_id'],
        'admission_reason': 'Flu'
    }, follow_redirects=True)

    # Attempt second admission into room 102
    resp = client.post('/admin/patients/admit', data={
        'full_name': 'Patient Two',
        'date_of_birth': '1993-03-03',
        'gender': 'Female',
        'phone': '555-0002',
        'room_id': sample_data['room102_id'],
        'doctor_id': sample_data['doctor_id'],
        'nurse_id': sample_data['nurse_id'],
        'admission_reason': 'Headache'
    }, follow_redirects=True)

    assert b"Selected room is no longer available" in resp.data

def test_doctor_initiates_discharge_creates_department_tasks(app, sample_data):
    """Test that doctor discharge initiation generates nursing and pharmacy tasks."""
    with app.app_context():
        doctor = db.session.get(User, sample_data['doctor_id'])
        nurse = db.session.get(User, sample_data['nurse_id'])
        patient = db.session.get(Patient, sample_data['patient_id'])
        room = db.session.get(Room, sample_data['room101_id'])

        adm = Admission(
            admission_number='ADM-TEST-001',
            patient_id=patient.id,
            room_id=room.id,
            admitting_doctor_id=doctor.id,
            assigned_nurse_id=nurse.id,
            status='Admitted',
            admission_reason='Hypertensive crisis'
        )
        db.session.add(adm)
        db.session.commit()

        # Doctor initiates discharge
        coord = DischargeService.initiate_discharge(
            admission_id=adm.id,
            doctor_user=doctor,
            clinical_notes="Blood pressure normalized to 120/80. Clinically ready.",
            follow_up_instructions="Continue amlodipine 5mg daily.",
            requires_nursing=True,
            requires_pharmacy=True,
            requires_laboratory=False
        )

        assert coord is not None
        assert coord.clinical_readiness_approved is True

        tasks = DepartmentTask.query.filter_by(admission_id=adm.id).all()
        assert len(tasks) >= 2
        depts = {t.department for t in tasks}
        assert 'Nursing' in depts
        assert 'Pharmacy' in depts

def test_discharge_readiness_and_premature_finalization_prevention(app, sample_data):
    """Test readiness engine blocks final discharge until all tasks are completed."""
    with app.app_context():
        doctor = db.session.get(User, sample_data['doctor_id'])
        nurse = db.session.get(User, sample_data['nurse_id'])
        patient = db.session.get(Patient, sample_data['patient_id'])
        room = db.session.get(Room, sample_data['room101_id'])
        admin = db.session.get(User, sample_data['admin_id'])

        adm = Admission(
            admission_number='ADM-TEST-002',
            patient_id=patient.id,
            room_id=room.id,
            admitting_doctor_id=doctor.id,
            assigned_nurse_id=nurse.id,
            status='Admitted',
            admission_reason='Chest pain'
        )
        db.session.add(adm)
        db.session.commit()

        DischargeService.initiate_discharge(
            admission_id=adm.id,
            doctor_user=doctor,
            clinical_notes="Stable",
            follow_up_instructions="Rest",
            requires_nursing=True,
            requires_pharmacy=True
        )

        # Premature discharge should fail because tasks are pending
        with pytest.raises(ValueError) as exc:
            DischargeService.finalize_final_discharge(
                admission_id=adm.id,
                admin_user=admin
            )
        assert "Patient cannot be discharged" in str(exc.value)

        # Complete all tasks
        tasks = DepartmentTask.query.filter_by(admission_id=adm.id).all()
        for t in tasks:
            t.status = 'Completed'
        db.session.commit()

        # Readiness should now be True
        readiness = DischargeService.calculate_discharge_readiness(adm.id)
        assert readiness['is_ready'] is True
        assert adm.status == 'Ready for Final Discharge'

        # Now finalize discharge
        DischargeService.finalize_final_discharge(
            admission_id=adm.id,
            admin_user=admin,
            discharge_summary="Patient successfully discharged.",
            release_room=True
        )

        assert adm.status == 'Discharged'
        assert adm.discharge_date is not None
        assert room.is_occupied is False
