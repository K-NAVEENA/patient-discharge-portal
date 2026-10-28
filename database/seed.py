from datetime import datetime, date, timedelta
from models import (
    db, User, Patient, Room, Admission, DischargeCoordination,
    DepartmentTask, CommunicationLog, BillingAccount, BillingItem, Payment, AuditEvent
)
from services.discharge_service import DischargeService
from services.billing_service import BillingService

def seed_database():
    """Populates realistic synthetic demonstration records."""
    db.create_all()

    # 1. Create Staff Users
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@hospital.local',
            'full_name': 'Administrator Dr. Arthur Pendelton',
            'role': 'admin',
            'department': 'Administration',
            'employee_id': 'ADM-001',
            'qualification': 'MHA, Hospital Administration',
            'approval_status': 'approved',
            'password': 'Admin@123'
        },
        {
            'username': 'dr_smith',
            'email': 'dr.smith@hospital.local',
            'full_name': 'Dr. John Smith',
            'role': 'doctor',
            'department': 'Cardiology',
            'employee_id': 'DOC-101',
            'qualification': 'MD, FACC Cardiology',
            'approval_status': 'approved',
            'password': 'Doctor@123'
        },
        {
            'username': 'dr_chen',
            'email': 'dr.chen@hospital.local',
            'full_name': 'Dr. Sarah Chen',
            'role': 'doctor',
            'department': 'Internal Medicine',
            'employee_id': 'DOC-102',
            'qualification': 'MD, Internal Medicine',
            'approval_status': 'approved',
            'password': 'Doctor@123'
        },
        {
            'username': 'nurse_emma',
            'email': 'emma.nurse@hospital.local',
            'full_name': 'Emma Watson',
            'role': 'nurse',
            'department': 'Nursing',
            'employee_id': 'NUR-201',
            'qualification': 'BSN, Registered Nurse',
            'approval_status': 'approved',
            'password': 'Nurse@123'
        },
        {
            'username': 'nurse_david',
            'email': 'david.nurse@hospital.local',
            'full_name': 'David Miller',
            'role': 'nurse',
            'department': 'Nursing',
            'employee_id': 'NUR-202',
            'qualification': 'RN, Intensive Care Certified',
            'approval_status': 'approved',
            'password': 'Nurse@123'
        },
        {
            'username': 'pharm_lisa',
            'email': 'lisa.pharm@hospital.local',
            'full_name': 'Lisa Ray',
            'role': 'pharmacy',
            'department': 'Pharmacy',
            'employee_id': 'PHM-301',
            'qualification': 'PharmD, Clinical Pharmacy',
            'approval_status': 'approved',
            'password': 'Pharm@123'
        },
        {
            'username': 'lab_robert',
            'email': 'robert.lab@hospital.local',
            'full_name': 'Robert Fox',
            'role': 'laboratory',
            'department': 'Laboratory',
            'employee_id': 'LAB-401',
            'qualification': 'MS, Medical Laboratory Science',
            'approval_status': 'approved',
            'password': 'Lab@123'
        },
        {
            'username': 'nurse_kevin',
            'email': 'kevin.vance@hospital.local',
            'full_name': 'Kevin Vance',
            'role': 'nurse',
            'department': 'Nursing',
            'employee_id': 'NUR-299',
            'qualification': 'RN',
            'approval_status': 'pending', # Pending registration for admin approval demo!
            'password': 'Nurse@123'
        }
    ]

    created_users = {}
    for udata in users_data:
        existing = User.query.filter_by(username=udata['username']).first()
        if not existing:
            u = User(
                username=udata['username'],
                email=udata['email'],
                full_name=udata['full_name'],
                role=udata['role'],
                department=udata['department'],
                employee_id=udata['employee_id'],
                qualification=udata['qualification'],
                approval_status=udata['approval_status'],
                is_active=True
            )
            u.set_password(udata['password'])
            db.session.add(u)
            db.session.flush()
            created_users[udata['username']] = u
        else:
            created_users[udata['username']] = existing

    # 2. Rooms
    rooms_data = [
        ('101', 'General Ward A', 'General Ward', 1200.0),
        ('102', 'General Ward A', 'General Ward', 1200.0),
        ('103', 'General Ward B', 'General Ward', 1200.0),
        ('201', 'Semi-Private 2nd Floor', 'Semi-Private', 2500.0),
        ('202', 'Semi-Private 2nd Floor', 'Semi-Private', 2500.0),
        ('203', 'Private Wing 2nd Floor', 'Private AC', 4500.0),
        ('204', 'Private Wing 2nd Floor', 'Private AC', 4500.0),
        ('301', 'Intensive Care Unit', 'ICU', 8500.0),
        ('302', 'Intensive Care Unit', 'ICU', 8500.0),
        ('401', 'Deluxe Wing 4th Floor', 'Deluxe Suite', 6000.0),
    ]

    rooms = {}
    for rnum, rward, rtype, rrate in rooms_data:
        existing = Room.query.filter_by(room_number=rnum).first()
        if not existing:
            r = Room(
                room_number=rnum,
                ward=rward,
                room_type=rtype,
                daily_rate=rrate,
                is_occupied=False
            )
            db.session.add(r)
            db.session.flush()
            rooms[rnum] = r
        else:
            rooms[rnum] = existing

    # 3. Create Demo Patients & Admissions
    # Patient 1: Eleanor Vance (Undergoing discharge, awaiting Pharmacy)
    pat1 = Patient.query.filter_by(patient_id='PID-2026-0001').first()
    if not pat1:
        # Create portal user for Eleanor
        p1_user = User(
            username='eleanor_vance',
            email='eleanor.vance@demo.local',
            full_name='Eleanor Vance',
            role='patient',
            department='Patient',
            approval_status='approved',
            is_active=True,
            must_change_password=False
        )
        p1_user.set_password('Patient@123')
        db.session.add(p1_user)
        db.session.flush()

        pat1 = Patient(
            patient_id='PID-2026-0001',
            full_name='Eleanor Vance',
            date_of_birth=date(1958, 4, 12),
            gender='Female',
            blood_group='O+',
            phone='555-0192',
            email='eleanor.vance@demo.local',
            address='742 Evergreen Terrace, Springfield',
            emergency_contact_name='Thomas Vance (Son)',
            emergency_contact_phone='555-0198',
            user_id=p1_user.id
        )
        db.session.add(pat1)
        db.session.flush()

        # Admission for Eleanor in Room 201
        adm1 = Admission(
            admission_number='ADM-2026-0001',
            patient_id=pat1.id,
            room_id=rooms['201'].id,
            admitting_doctor_id=created_users['dr_smith'].id,
            assigned_nurse_id=created_users['nurse_emma'].id,
            admission_date=datetime.utcnow() - timedelta(days=4),
            status='Awaiting Departmental Clearance',
            admission_reason='Acute congestive heart failure exacerbation, dyspnea on exertion.',
            initial_diagnosis='Class III CHF, hypertension'
        )
        db.session.add(adm1)
        db.session.flush()

        rooms['201'].is_occupied = True
        rooms['201'].current_patient_id = pat1.id
        rooms['201'].current_admission_id = adm1.id

        # Discharge coordination
        coord1 = DischargeCoordination(
            admission_id=adm1.id,
            initiated_by_doctor_id=created_users['dr_smith'].id,
            initiated_at=datetime.utcnow() - timedelta(hours=6),
            clinical_readiness_approved=True,
            clinical_notes="Patient is clinically compensated. Stable oxygen saturation on room air, ambulatory.",
            follow_up_instructions="Low sodium diet (<2g/day), daily weights, follow up in Cardiology Clinic in 7 days.",
            requires_nursing=True,
            requires_pharmacy=True,
            requires_laboratory=False,
            nursing_cleared=True,
            nursing_cleared_at=datetime.utcnow() - timedelta(hours=2),
            nursing_cleared_by_id=created_users['nurse_emma'].id,
            pharmacy_cleared=False,
            is_ready_for_discharge=False
        )
        db.session.add(coord1)
        db.session.flush()

        # Tasks for Eleanor
        # Nursing task - completed
        t1 = DepartmentTask(
            task_code='TSK-NUR-0101',
            admission_id=adm1.id,
            discharge_coordination_id=coord1.id,
            department='Nursing',
            title='Discharge Vitals & IV Removal',
            description='Verify BP/Pulse and safely remove peripheral catheter.',
            status='Completed',
            completed_by_user_id=created_users['nurse_emma'].id,
            completed_at=datetime.utcnow() - timedelta(hours=2),
            remarks='Catheter removed, vitals: BP 124/78, Pulse 72 bpm.'
        )
        # Pharmacy task - pending
        t2 = DepartmentTask(
            task_code='TSK-PHM-0102',
            admission_id=adm1.id,
            discharge_coordination_id=coord1.id,
            department='Pharmacy',
            title='Medication Reconciliation & Dispensing',
            description='Prepare 30-day supply of Furosemide and Carvedilol.',
            status='Pending',
            remarks='Awaiting stock verification from central depot.'
        )
        db.session.add_all([t1, t2])

        # Communication Log
        c1 = CommunicationLog(
            patient_id=pat1.id,
            admission_id=adm1.id,
            discharge_coordination_id=coord1.id,
            sender_id=created_users['dr_smith'].id,
            sender_role='doctor',
            source_department='Cardiology',
            target_department='All Staff',
            message='Patient Eleanor Vance cleared clinically. Discharged on reduced diuretic dose.',
            log_type='clearance'
        )
        c2 = CommunicationLog(
            patient_id=pat1.id,
            admission_id=adm1.id,
            discharge_coordination_id=coord1.id,
            sender_id=created_users['nurse_emma'].id,
            sender_role='nurse',
            source_department='Nursing',
            target_department='Pharmacy',
            message='Patient has questions regarding medication scheduling. Please prioritize discharge counseling.',
            log_type='message'
        )
        db.session.add_all([c1, c2])

        # Billing for Eleanor
        BillingService.sync_room_charges(adm1, recorded_by_user_id=created_users['admin'].id)
        BillingService.record_payment(
            billing_account_id=adm1.billing_account.id,
            amount=5000.0,
            payment_method='Insurance',
            recorded_by_user_id=created_users['admin'].id,
            transaction_id='INS-POL-882194',
            notes='Initial pre-authorization insurance advance'
        )

    # Patient 2: Marcus Brody (Ready for Final Discharge)
    pat2 = Patient.query.filter_by(patient_id='PID-2026-0002').first()
    if not pat2:
        p2_user = User(
            username='marcus_brody',
            email='marcus.brody@demo.local',
            full_name='Marcus Brody',
            role='patient',
            department='Patient',
            approval_status='approved',
            is_active=True,
            must_change_password=False
        )
        p2_user.set_password('Patient@123')
        db.session.add(p2_user)
        db.session.flush()

        pat2 = Patient(
            patient_id='PID-2026-0002',
            full_name='Marcus Brody',
            date_of_birth=date(1982, 9, 23),
            gender='Male',
            blood_group='A-',
            phone='555-0814',
            email='marcus.brody@demo.local',
            address='1204 Oak Ridge Way, Metro City',
            emergency_contact_name='Sarah Brody (Spouse)',
            emergency_contact_phone='555-0819',
            user_id=p2_user.id
        )
        db.session.add(pat2)
        db.session.flush()

        adm2 = Admission(
            admission_number='ADM-2026-0002',
            patient_id=pat2.id,
            room_id=rooms['203'].id,
            admitting_doctor_id=created_users['dr_chen'].id,
            assigned_nurse_id=created_users['nurse_david'].id,
            admission_date=datetime.utcnow() - timedelta(days=3),
            status='Ready for Final Discharge',
            admission_reason='Laparoscopic appendectomy post acute uncomplicated appendicitis.',
            initial_diagnosis='Acute appendicitis'
        )
        db.session.add(adm2)
        db.session.flush()

        rooms['203'].is_occupied = True
        rooms['203'].current_patient_id = pat2.id
        rooms['203'].current_admission_id = adm2.id

        coord2 = DischargeCoordination(
            admission_id=adm2.id,
            initiated_by_doctor_id=created_users['dr_chen'].id,
            initiated_at=datetime.utcnow() - timedelta(hours=10),
            clinical_readiness_approved=True,
            clinical_notes="Surgical incision clean, healing well. Tolerating regular diet, afebrile.",
            follow_up_instructions="Keep dressing dry for 48 hours. Remove steristrips in 10 days. Avoid lifting > 10 lbs.",
            requires_nursing=True,
            requires_pharmacy=True,
            requires_laboratory=True,
            nursing_cleared=True,
            nursing_cleared_at=datetime.utcnow() - timedelta(hours=3),
            nursing_cleared_by_id=created_users['nurse_david'].id,
            pharmacy_cleared=True,
            pharmacy_cleared_at=datetime.utcnow() - timedelta(hours=2),
            pharmacy_cleared_by_id=created_users['pharm_lisa'].id,
            laboratory_cleared=True,
            laboratory_cleared_at=datetime.utcnow() - timedelta(hours=1),
            laboratory_cleared_by_id=created_users['lab_robert'].id,
            is_ready_for_discharge=True
        )
        db.session.add(coord2)
        db.session.flush()

        t2_1 = DepartmentTask(
            task_code='TSK-NUR-0201',
            admission_id=adm2.id,
            discharge_coordination_id=coord2.id,
            department='Nursing',
            title='Wound Inspection & Home Care Education',
            description='Inspect laparoscopic ports and provide post-op guidance.',
            status='Completed',
            completed_by_user_id=created_users['nurse_david'].id,
            completed_at=datetime.utcnow() - timedelta(hours=3),
            remarks='Wound sites intact, no erythema.'
        )
        t2_2 = DepartmentTask(
            task_code='TSK-PHM-0202',
            admission_id=adm2.id,
            discharge_coordination_id=coord2.id,
            department='Pharmacy',
            title='Post-op Pain Management Dispensation',
            description='Dispense Acetaminophen and Cefalexin course.',
            status='Completed',
            completed_by_user_id=created_users['pharm_lisa'].id,
            completed_at=datetime.utcnow() - timedelta(hours=2),
            remarks='Medications dispensed and patient educated.'
        )
        t2_3 = DepartmentTask(
            task_code='TSK-LAB-0203',
            admission_id=adm2.id,
            discharge_coordination_id=coord2.id,
            department='Laboratory',
            title='Post-op Complete Blood Count',
            description='Confirm normal leukocyte levels.',
            status='Completed',
            completed_by_user_id=created_users['lab_robert'].id,
            completed_at=datetime.utcnow() - timedelta(hours=1),
            remarks='WBC normal (7.2 x 10^9/L).'
        )
        db.session.add_all([t2_1, t2_2, t2_3])

        BillingService.sync_room_charges(adm2, recorded_by_user_id=created_users['admin'].id)
        BillingService.add_billing_item(
            billing_account_id=adm2.billing_account.id,
            category='Pharmacy',
            description='Post-op Oral Antibiotics & Analgesics',
            unit_price=850.0,
            quantity=1.0,
            added_by_user_id=created_users['pharm_lisa'].id
        )
        BillingService.add_billing_item(
            billing_account_id=adm2.billing_account.id,
            category='Laboratory',
            description='Post-op CBC & Electrolyte Panel',
            unit_price=1200.0,
            quantity=1.0,
            added_by_user_id=created_users['lab_robert'].id
        )

    # Patient 3: Sophia Patel (Newly Admitted)
    pat3 = Patient.query.filter_by(patient_id='PID-2026-0003').first()
    if not pat3:
        pat3 = Patient(
            patient_id='PID-2026-0003',
            full_name='Sophia Patel',
            date_of_birth=date(1995, 11, 3),
            gender='Female',
            blood_group='B+',
            phone='555-0371',
            email='sophia.patel@demo.local',
            address='88 Highland Park Blvd, Riverdale',
            emergency_contact_name='Aarav Patel (Brother)',
            emergency_contact_phone='555-0379'
        )
        db.session.add(pat3)
        db.session.flush()

        adm3 = Admission(
            admission_number='ADM-2026-0003',
            patient_id=pat3.id,
            room_id=rooms['101'].id,
            admitting_doctor_id=created_users['dr_chen'].id,
            assigned_nurse_id=created_users['nurse_emma'].id,
            admission_date=datetime.utcnow() - timedelta(days=1),
            status='Admitted',
            admission_reason='Community-acquired lobar pneumonia, persistent fever 39°C.',
            initial_diagnosis='Right lower lobe pneumonia'
        )
        db.session.add(adm3)
        db.session.flush()

        rooms['101'].is_occupied = True
        rooms['101'].current_patient_id = pat3.id
        rooms['101'].current_admission_id = adm3.id

        BillingService.sync_room_charges(adm3, recorded_by_user_id=created_users['admin'].id)

    # Patient 4: James Wilson (Discharged Historical Record)
    pat4 = Patient.query.filter_by(patient_id='PID-2026-0004').first()
    if not pat4:
        pat4 = Patient(
            patient_id='PID-2026-0004',
            full_name='James Wilson',
            date_of_birth=date(1975, 2, 17),
            gender='Male',
            blood_group='AB+',
            phone='555-0552',
            email='james.wilson@demo.local',
            address='45 Baker Street, Highview'
        )
        db.session.add(pat4)
        db.session.flush()

        adm4 = Admission(
            admission_number='ADM-2026-0004',
            patient_id=pat4.id,
            room_id=rooms['102'].id,
            admitting_doctor_id=created_users['dr_smith'].id,
            assigned_nurse_id=created_users['nurse_david'].id,
            admission_date=datetime.utcnow() - timedelta(days=14),
            discharge_date=datetime.utcnow() - timedelta(days=8),
            status='Discharged',
            admission_reason='Unstable angina, evaluated and stabilized.',
            initial_diagnosis='Coronary artery disease, angina pectoris',
            discharged_by_user_id=created_users['admin'].id,
            discharge_summary='Patient responded well to medical therapy. Angiogram deferred. Prescribed statin and beta blocker.'
        )
        db.session.add(adm4)
        db.session.flush()

        coord4 = DischargeCoordination(
            admission_id=adm4.id,
            initiated_by_doctor_id=created_users['dr_smith'].id,
            initiated_at=datetime.utcnow() - timedelta(days=9),
            clinical_readiness_approved=True,
            requires_nursing=True,
            requires_pharmacy=True,
            nursing_cleared=True,
            pharmacy_cleared=True,
            is_ready_for_discharge=True,
            is_finalized=True,
            final_discharged_at=datetime.utcnow() - timedelta(days=8),
            final_discharged_by_id=created_users['admin'].id
        )
        db.session.add(coord4)
        db.session.flush()

        BillingService.sync_room_charges(adm4, recorded_by_user_id=created_users['admin'].id)
        # Settle bill
        BillingService.record_payment(
            billing_account_id=adm4.billing_account.id,
            amount=adm4.billing_account.total_amount,
            payment_method='Credit Card',
            recorded_by_user_id=created_users['admin'].id,
            transaction_id='TXN-CC-99120',
            notes='Paid in full at final discharge'
        )

    db.session.commit()
