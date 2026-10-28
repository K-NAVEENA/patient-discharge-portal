from datetime import datetime
from flask import Blueprint, request, redirect, url_for, flash, g, jsonify
from models import db, CommunicationLog, Admission, Patient
from routes.auth import login_required
from services.notification_service import NotificationService

communication_bp = Blueprint('communication', __name__, url_prefix='/communication')

@communication_bp.route('/send', methods=['POST'])
@login_required
def send_message():
    admission_id = request.form.get('admission_id')
    target_department = request.form.get('target_department', 'All Staff').strip()
    message = request.form.get('message', '').strip()
    redirect_url = request.form.get('redirect_url', '/')

    if not admission_id or not message:
        flash('Message text is required.', 'danger')
        return redirect(redirect_url)

    admission = Admission.query.get_or_404(admission_id)

    # Determine source department
    dept = g.current_user.department or g.current_user.role.title()

    comm = CommunicationLog(
        patient_id=admission.patient_id,
        admission_id=admission.id,
        discharge_coordination_id=admission.discharge_coordination.id if admission.discharge_coordination else None,
        sender_id=g.current_user.id,
        sender_role=g.current_user.role,
        source_department=dept,
        target_department=target_department,
        message=message,
        log_type='message',
        created_at=datetime.utcnow()
    )
    db.session.add(comm)

    # Dispatch notification if targeted
    if target_department in ['Doctor', 'Medical Staff']:
        NotificationService.create_notification(
            recipient_user_id=admission.admitting_doctor_id,
            event_type='message_received',
            title=f"New Message from {g.current_user.full_name} ({dept})",
            message=f"Regarding patient {admission.patient.full_name}: {message[:100]}",
            link_url=f"/doctor/patient/{admission.id}"
        )
    elif target_department in ['Nursing', 'Nurse']:
        NotificationService.create_notification(
            recipient_user_id=admission.assigned_nurse_id,
            event_type='message_received',
            title=f"New Nursing Note from {g.current_user.full_name}",
            message=f"Regarding patient {admission.patient.full_name}: {message[:100]}",
            link_url=f"/nurse/discharge/{admission.id}"
        )
    elif target_department == 'Pharmacy':
        NotificationService.notify_department(
            department='Pharmacy',
            event_type='message_received',
            title=f"Pharmacy Message: {admission.patient.full_name}",
            message=f"From {g.current_user.full_name}: {message[:100]}",
            link_url=f"/pharmacy/discharge/{admission.id}"
        )
    elif target_department == 'Laboratory':
        NotificationService.notify_department(
            department='Laboratory',
            event_type='message_received',
            title=f"Laboratory Message: {admission.patient.full_name}",
            message=f"From {g.current_user.full_name}: {message[:100]}",
            link_url=f"/laboratory/discharge/{admission.id}"
        )

    db.session.commit()
    flash('Interdepartmental communication log added.', 'success')
    return redirect(redirect_url)

@communication_bp.route('/<int:log_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_message(log_id):
    comm = CommunicationLog.query.get_or_404(log_id)
    comm.is_acknowledged = True
    comm.acknowledged_by_id = g.current_user.id
    comm.acknowledged_at = datetime.utcnow()
    db.session.commit()

    redirect_url = request.form.get('redirect_url', '/')
    flash('Communication acknowledged.', 'info')
    return redirect(redirect_url)
