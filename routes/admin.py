import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from sqlalchemy import or_, and_, func
from models import (
    db, User, Patient, Room, Admission, DischargeCoordination,
    DepartmentTask, CommunicationLog, BillingAccount, AuditEvent
)
from routes.auth import role_required
from services.notification_service import NotificationService
from services.billing_service import BillingService
from services.discharge_service import DischargeService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    # Real database statistics
    total_admitted = Admission.query.filter(Admission.status != 'Discharged').count()
    undergoing_discharge = Admission.query.filter(
        Admission.status.in_(['Discharge In Progress', 'Awaiting Departmental Clearance', 'Ready for Final Discharge'])
    ).count()
    awaiting_clearance = Admission.query.filter_by(status='Awaiting Departmental Clearance').count()
    ready_for_discharge = Admission.query.filter_by(status='Ready for Final Discharge').count()
    total_discharged = Admission.query.filter_by(status='Discharged').count()
    pending_staff = User.query.filter_by(approval_status='pending').count()

    total_rooms = Room.query.count()
    occupied_rooms = Room.query.filter_by(is_occupied=True).count()
    occupancy_pct = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0

    total_outstanding = db.session.query(func.sum(BillingAccount.balance_due)).scalar() or 0.0

    # Recent active admissions
    active_admissions = Admission.query.filter(Admission.status != 'Discharged')\
        .order_by(Admission.admission_date.desc()).limit(10).all()

    # Discharge workflow queue
    discharge_queue = Admission.query.filter(
        Admission.status.in_(['Discharge In Progress', 'Awaiting Departmental Clearance', 'Ready for Final Discharge'])
    ).order_by(Admission.admission_date.asc()).all()

    return render_template(
        'admin_dashboard.html',
        total_admitted=total_admitted,
        undergoing_discharge=undergoing_discharge,
        awaiting_clearance=awaiting_clearance,
        ready_for_discharge=ready_for_discharge,
        total_discharged=total_discharged,
        pending_staff=pending_staff,
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        occupancy_pct=occupancy_pct,
        total_outstanding=round(total_outstanding, 2),
        active_admissions=active_admissions,
        discharge_queue=discharge_queue
    )

@admin_bp.route('/patients')
@role_required('admin')
def patients_list():
    query_str = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    admissions_query = Admission.query.join(Admission.patient).join(Admission.room)

    if query_str:
        admissions_query = admissions_query.filter(
            or_(
                Patient.patient_id.ilike(f"%{query_str}%"),
                Patient.full_name.ilike(f"%{query_str}%"),
                Room.room_number.ilike(f"%{query_str}%"),
                Admission.admission_number.ilike(f"%{query_str}%")
            )
        )

    if status_filter:
        admissions_query = admissions_query.filter(Admission.status == status_filter)

    if from_date:
        try:
            f_dt = datetime.strptime(from_date, '%Y-%m-%d')
            admissions_query = admissions_query.filter(Admission.admission_date >= f_dt)
        except ValueError:
            pass

    if to_date:
        try:
            t_dt = datetime.strptime(to_date, '%Y-%m-%d')
            # include full day
            t_dt = datetime(t_dt.year, t_dt.month, t_dt.day, 23, 59, 59)
            admissions_query = admissions_query.filter(Admission.admission_date <= t_dt)
        except ValueError:
            pass

    admissions = admissions_query.order_by(Admission.admission_date.desc()).all()
    return render_template('patients_list.html', admissions=admissions,
                           query_str=query_str, status_filter=status_filter,
                           from_date=from_date, to_date=to_date)

@admin_bp.route('/patients/admit', methods=['GET', 'POST'])
@role_required('admin')
def admit_patient():
    available_rooms = Room.query.filter_by(is_occupied=False).all()
    doctors = User.query.filter_by(role='doctor', approval_status='approved', is_active=True).all()
    nurses = User.query.filter_by(role='nurse', approval_status='approved', is_active=True).all()

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        dob_str = request.form.get('date_of_birth', '').strip()
        gender = request.form.get('gender', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip().lower()
        address = request.form.get('address', '').strip()
        emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
        emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()

        room_id = request.form.get('room_id')
        doctor_id = request.form.get('doctor_id')
        nurse_id = request.form.get('nurse_id')
        admission_reason = request.form.get('admission_reason', '').strip()
        admission_remarks = request.form.get('admission_remarks', '').strip()
        create_portal_account = request.form.get('create_portal_account') == 'on'
        temp_password = request.form.get('temp_password', '').strip()

        if not full_name or not dob_str or not gender or not phone or not room_id or not doctor_id or not nurse_id or not admission_reason:
            flash('Please complete all required fields (Patient Info, Room, Doctor, Nurse, Reason).', 'danger')
            return render_template('admit_patient.html', available_rooms=available_rooms, doctors=doctors, nurses=nurses)

        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date of birth format.', 'danger')
            return render_template('admit_patient.html', available_rooms=available_rooms, doctors=doctors, nurses=nurses)

        # Room check (prevent double occupancy)
        room = Room.query.get(room_id)
        if not room or room.is_occupied:
            flash('Selected room is no longer available. Please choose an unoccupied room.', 'danger')
            return render_template('admit_patient.html', available_rooms=Room.query.filter_by(is_occupied=False).all(), doctors=doctors, nurses=nurses)

        # Check existing patient by phone / email or create new
        existing_patient = None
        if email:
            existing_patient = Patient.query.filter_by(email=email).first()
        if not existing_patient and phone:
            existing_patient = Patient.query.filter_by(phone=phone, full_name=full_name).first()

        if existing_patient:
            patient = existing_patient
            # Check if patient already has an active non-discharged admission
            active_adm = Admission.query.filter_by(patient_id=patient.id).filter(Admission.status != 'Discharged').first()
            if active_adm:
                flash(f'Patient {patient.full_name} is already currently admitted in Room {active_adm.room.room_number}.', 'danger')
                return render_template('admit_patient.html', available_rooms=available_rooms, doctors=doctors, nurses=nurses)
        else:
            # Generate Unique Patient ID
            curr_year = datetime.utcnow().year
            pat_count = Patient.query.count() + 1
            patient_id_code = f"PID-{curr_year}-{pat_count:04d}"

            patient = Patient(
                patient_id=patient_id_code,
                full_name=full_name,
                date_of_birth=dob,
                gender=gender,
                blood_group=blood_group,
                phone=phone,
                email=email or None,
                address=address,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone
            )
            db.session.add(patient)
            db.session.flush()

        # Handle Patient Portal Account Activation if requested
        if create_portal_account and not patient.user_id:
            portal_username = (email.split('@')[0] if email else f"p_{patient.patient_id.lower().replace('-', '_')}")
            # Ensure unique username
            base_u = portal_username
            ctr = 1
            while User.query.filter_by(username=portal_username).first():
                portal_username = f"{base_u}{ctr}"
                ctr += 1

            p_pwd = temp_password if temp_password else "Hospital@123"
            p_user = User(
                username=portal_username,
                email=email or f"{portal_username}@patientportal.local",
                full_name=patient.full_name,
                role='patient',
                department='Patient',
                phone=patient.phone,
                approval_status='approved',
                is_active=True,
                must_change_password=True # Enforce password change on first login!
            )
            p_user.set_password(p_pwd)
            db.session.add(p_user)
            db.session.flush()
            patient.user_id = p_user.id

        # Generate Admission Number
        curr_year = datetime.utcnow().year
        adm_count = Admission.query.count() + 1
        admission_code = f"ADM-{curr_year}-{adm_count:04d}"

        admission = Admission(
            admission_number=admission_code,
            patient_id=patient.id,
            room_id=room.id,
            admitting_doctor_id=int(doctor_id),
            assigned_nurse_id=int(nurse_id),
            admission_date=datetime.utcnow(),
            status='Admitted',
            admission_reason=admission_reason,
            admission_remarks=admission_remarks
        )
        db.session.add(admission)
        db.session.flush()

        # Allocate room
        room.is_occupied = True
        room.current_patient_id = patient.id
        room.current_admission_id = admission.id

        # Initialize Billing
        BillingService.sync_room_charges(admission, recorded_by_user_id=g.current_user.id)

        # Notify Assigned Doctor and Nurse
        NotificationService.create_notification(
            recipient_user_id=int(doctor_id),
            event_type='patient_assigned',
            title='New Patient Assigned',
            message=f"Patient {patient.full_name} admitted to Room {room.room_number}. Assigned to your care.",
            link_url=f"/doctor/patient/{admission.id}"
        )
        NotificationService.create_notification(
            recipient_user_id=int(nurse_id),
            event_type='patient_assigned',
            title='New Patient Assigned to Ward Care',
            message=f"Patient {patient.full_name} admitted in Room {room.room_number}.",
            link_url=f"/nurse/dashboard"
        )

        # Communication Log
        comm = CommunicationLog(
            patient_id=patient.id,
            admission_id=admission.id,
            sender_id=g.current_user.id,
            sender_role='admin',
            source_department='Admissions',
            target_department='All Staff',
            message=f"Patient {patient.full_name} ({patient.patient_id}) admitted to Room {room.room_number} under Dr. {admission.admitting_doctor.full_name}.",
            log_type='status_change'
        )
        db.session.add(comm)

        # Audit Event
        audit = AuditEvent(
            user_id=g.current_user.id,
            action='PATIENT_ADMITTED',
            entity_type='Admission',
            entity_id=str(admission.id),
            details=f"Admitted {patient.full_name} to room {room.room_number}."
        )
        db.session.add(audit)

        db.session.commit()
        flash(f'Patient {patient.full_name} admitted successfully with ID {patient.patient_id} in Room {room.room_number}!', 'success')
        return redirect(url_for('admin.view_patient', patient_id=patient.id))

    return render_template('admit_patient.html', available_rooms=available_rooms, doctors=doctors, nurses=nurses)

@admin_bp.route('/patients/<int:patient_id>')
@role_required('admin')
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    admissions = patient.admissions.all()
    current_adm = patient.current_admission
    return render_template('patient_details.html', patient=patient, admissions=admissions, current_adm=current_adm)

@admin_bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.full_name = request.form.get('full_name', patient.full_name).strip()
        patient.phone = request.form.get('phone', patient.phone).strip()
        patient.email = request.form.get('email', patient.email).strip() or None
        patient.address = request.form.get('address', patient.address).strip()
        patient.emergency_contact_name = request.form.get('emergency_contact_name', patient.emergency_contact_name).strip()
        patient.emergency_contact_phone = request.form.get('emergency_contact_phone', patient.emergency_contact_phone).strip()

        audit = AuditEvent(
            user_id=g.current_user.id,
            action='PATIENT_UPDATED',
            entity_type='Patient',
            entity_id=str(patient.id),
            details=f"Admin updated demographic details for patient {patient.patient_id}."
        )
        db.session.add(audit)
        db.session.commit()
        flash('Patient details updated successfully.', 'success')
        return redirect(url_for('admin.view_patient', patient_id=patient.id))

    return render_template('edit_patient.html', patient=patient)

@admin_bp.route('/patients/<int:patient_id>/history')
@role_required(['admin', 'doctor', 'nurse'])
def patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    admissions = Admission.query.filter_by(patient_id=patient.id).order_by(Admission.admission_date.desc()).all()
    return render_template('patient_history.html', patient=patient, admissions=admissions)

@admin_bp.route('/rooms')
@role_required('admin')
def rooms():
    all_rooms = Room.query.order_by(Room.ward, Room.room_number).all()
    return render_template('rooms.html', rooms=all_rooms)

@admin_bp.route('/rooms/add', methods=['POST'])
@role_required('admin')
def add_room():
    room_number = request.form.get('room_number', '').strip()
    ward = request.form.get('ward', '').strip()
    room_type = request.form.get('room_type', '').strip()
    daily_rate = float(request.form.get('daily_rate', 1500.0))

    if not room_number or not ward or not room_type:
        flash('All room fields are required.', 'danger')
        return redirect(url_for('admin.rooms'))

    if Room.query.filter_by(room_number=room_number).first():
        flash(f'Room {room_number} already exists.', 'danger')
        return redirect(url_for('admin.rooms'))

    new_room = Room(
        room_number=room_number,
        ward=ward,
        room_type=room_type,
        daily_rate=daily_rate,
        is_occupied=False
    )
    db.session.add(new_room)
    db.session.commit()
    flash(f'Room {room_number} added successfully.', 'success')
    return redirect(url_for('admin.rooms'))

@admin_bp.route('/staff')
@role_required('admin')
def staff():
    pending_staff = User.query.filter_by(approval_status='pending').all()
    approved_staff = User.query.filter(User.role != 'admin', User.role != 'patient', User.approval_status != 'pending')\
        .order_by(User.role, User.full_name).all()
    return render_template('staff_approvals.html', pending_staff=pending_staff, approved_staff=approved_staff)

@admin_bp.route('/staff/<int:user_id>/approve', methods=['POST'])
@role_required('admin')
def approve_staff(user_id):
    staff_user = User.query.get_or_404(user_id)
    staff_user.approval_status = 'approved'
    staff_user.is_active = True

    NotificationService.create_notification(
        recipient_user_id=staff_user.id,
        event_type='staff_approved',
        title='Account Approved',
        message=f'Your staff registration as {staff_user.role.title()} has been approved. You can now log in and access your portal dashboard.',
        link_url='/auth/login'
    )

    audit = AuditEvent(
        user_id=g.current_user.id,
        action='STAFF_APPROVED',
        entity_type='User',
        entity_id=str(staff_user.id),
        details=f"Admin {g.current_user.full_name} approved staff account {staff_user.username} ({staff_user.role})."
    )
    db.session.add(audit)
    db.session.commit()

    flash(f'Staff account {staff_user.full_name} ({staff_user.role.title()}) approved successfully.', 'success')
    return redirect(url_for('admin.staff'))

@admin_bp.route('/staff/<int:user_id>/reject', methods=['POST'])
@role_required('admin')
def reject_staff(user_id):
    staff_user = User.query.get_or_404(user_id)
    staff_user.approval_status = 'rejected'
    staff_user.is_active = False

    audit = AuditEvent(
        user_id=g.current_user.id,
        action='STAFF_REJECTED',
        entity_type='User',
        entity_id=str(staff_user.id),
        details=f"Admin rejected staff registration for {staff_user.username}."
    )
    db.session.add(audit)
    db.session.commit()

    flash(f'Registration request for {staff_user.full_name} has been rejected.', 'info')
    return redirect(url_for('admin.staff'))

@admin_bp.route('/staff/<int:user_id>/toggle-status', methods=['POST'])
@role_required('admin')
def toggle_staff_status(user_id):
    staff_user = User.query.get_or_404(user_id)
    if staff_user.role == 'admin':
        flash('Cannot deactivate an administrator account from this interface.', 'danger')
        return redirect(url_for('admin.staff'))

    staff_user.is_active = not staff_user.is_active
    db.session.commit()
    state = 'activated' if staff_user.is_active else 'deactivated'
    flash(f'User {staff_user.full_name} has been {state}.', 'info')
    return redirect(url_for('admin.staff'))

@admin_bp.route('/discharge/<int:admission_id>')
@role_required('admin')
def discharge_details(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    coordination = admission.discharge_coordination
    tasks = admission.tasks.all()
    communications = admission.communication_logs.order_by(CommunicationLog.created_at.desc()).all()
    billing_account = BillingService.sync_room_charges(admission)

    # Re-evaluate readiness
    readiness = None
    if coordination:
        readiness = DischargeService.calculate_discharge_readiness(admission.id)

    return render_template(
        'discharge_details.html',
        admission=admission,
        coordination=coordination,
        tasks=tasks,
        communications=communications,
        billing_account=billing_account,
        readiness=readiness
    )

@admin_bp.route('/discharge/<int:admission_id>/finalize', methods=['POST'])
@role_required('admin')
def finalize_discharge(admission_id):
    discharge_summary = request.form.get('discharge_summary', '').strip()
    release_room = request.form.get('release_room') == 'on'

    try:
        DischargeService.finalize_final_discharge(
            admission_id=admission_id,
            admin_user=g.current_user,
            discharge_summary=discharge_summary,
            release_room=release_room
        )
        flash('Patient final discharge finalized successfully! Room released and patient records preserved.', 'success')
    except Exception as e:
        flash(f'Cannot finalize discharge: {str(e)}', 'danger')

    return redirect(url_for('admin.discharge_details', admission_id=admission_id))

@admin_bp.route('/patients/<int:patient_id>/activate-portal', methods=['POST'])
@role_required('admin')
def activate_patient_portal(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.user_id:
        flash('Patient already has a portal user account.', 'info')
        return redirect(url_for('admin.view_patient', patient_id=patient.id))

    temp_password = request.form.get('temp_password', 'Patient@123').strip()
    email = patient.email or f"{patient.patient_id.lower().replace('-', '_')}@patientportal.local"
    username = patient.email.split('@')[0] if patient.email else patient.patient_id.lower().replace('-', '_')

    # Ensure unique username
    base_u = username
    ctr = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_u}_{ctr}"
        ctr += 1

    p_user = User(
        username=username,
        email=email,
        full_name=patient.full_name,
        role='patient',
        department='Patient',
        phone=patient.phone,
        approval_status='approved',
        is_active=True,
        must_change_password=True
    )
    p_user.set_password(temp_password)
    db.session.add(p_user)
    db.session.flush()

    patient.user_id = p_user.id
    db.session.commit()

    flash(f"Patient portal activated! Username: '{username}' with temporary password provided.", 'success')
    return redirect(url_for('admin.view_patient', patient_id=patient.id))
