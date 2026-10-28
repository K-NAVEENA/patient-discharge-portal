from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db, Admission, Patient, DischargeCoordination, DepartmentTask, CommunicationLog
from routes.auth import role_required
from services.discharge_service import DischargeService

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/dashboard')
@role_required(['doctor', 'admin'])
def dashboard():
    doctor_id = g.current_user.id

    # Active assigned patients
    active_admissions = Admission.query.filter_by(admitting_doctor_id=doctor_id)\
        .filter(Admission.status != 'Discharged')\
        .order_by(Admission.admission_date.desc()).all()

    # Patients undergoing discharge
    discharge_patients = [a for a in active_admissions if a.status in [
        'Discharge In Progress', 'Awaiting Departmental Clearance', 'Ready for Final Discharge'
    ]]

    # Ready for final discharge count
    ready_count = sum(1 for a in active_admissions if a.status == 'Ready for Final Discharge')

    # Recently discharged patients treated by this doctor
    past_discharged = Admission.query.filter_by(admitting_doctor_id=doctor_id, status='Discharged')\
        .order_by(Admission.discharge_date.desc()).limit(5).all()

    return render_template(
        'doctor_dashboard.html',
        active_admissions=active_admissions,
        discharge_patients=discharge_patients,
        ready_count=ready_count,
        past_discharged=past_discharged
    )

@doctor_bp.route('/patient/<int:admission_id>')
@role_required(['doctor', 'admin'])
def patient_detail(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    # Check assignment (admin or assigned doctor)
    if g.current_user.role != 'admin' and admission.admitting_doctor_id != g.current_user.id:
        flash('You are not authorized to view patients assigned to another doctor.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    coordination = admission.discharge_coordination
    tasks = admission.tasks.all() if coordination else []
    communications = admission.communication_logs.order_by(CommunicationLog.created_at.desc()).all()

    readiness = None
    if coordination:
        readiness = DischargeService.calculate_discharge_readiness(admission.id)

    return render_template(
        'doctor_patient_detail.html',
        admission=admission,
        coordination=coordination,
        tasks=tasks,
        communications=communications,
        readiness=readiness
    )

@doctor_bp.route('/patient/<int:admission_id>/initiate-discharge', methods=['POST'])
@role_required(['doctor', 'admin'])
def initiate_discharge(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    if g.current_user.role != 'admin' and admission.admitting_doctor_id != g.current_user.id:
        flash('Unauthorized to initiate discharge for this patient.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    clinical_notes = request.form.get('clinical_notes', '').strip()
    follow_up_instructions = request.form.get('follow_up_instructions', '').strip()
    requires_nursing = request.form.get('requires_nursing') == 'on'
    requires_pharmacy = request.form.get('requires_pharmacy') == 'on'
    requires_laboratory = request.form.get('requires_laboratory') == 'on'

    if not clinical_notes:
        flash('Please provide clinical discharge notes justifying clinical readiness.', 'danger')
        return redirect(url_for('doctor.patient_detail', admission_id=admission.id))

    try:
        DischargeService.initiate_discharge(
            admission_id=admission.id,
            doctor_user=g.current_user,
            clinical_notes=clinical_notes,
            follow_up_instructions=follow_up_instructions,
            requires_nursing=requires_nursing,
            requires_pharmacy=requires_pharmacy,
            requires_laboratory=requires_laboratory
        )
        flash('Clinical discharge readiness recorded! Departmental clearance tasks dispatched.', 'success')
    except Exception as e:
        flash(f'Error initiating discharge: {str(e)}', 'danger')

    return redirect(url_for('doctor.patient_detail', admission_id=admission.id))
