from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db, Admission, DepartmentTask, CommunicationLog, DischargeCoordination
from routes.auth import role_required
from services.discharge_service import DischargeService

nurse_bp = Blueprint('nurse', __name__, url_prefix='/nurse')

@nurse_bp.route('/dashboard')
@role_required(['nurse', 'admin'])
def dashboard():
    nurse_id = g.current_user.id

    # Active assigned patients
    active_admissions = Admission.query.filter_by(assigned_nurse_id=nurse_id)\
        .filter(Admission.status != 'Discharged')\
        .order_by(Admission.admission_date.desc()).all()

    # Discharge active patients
    discharge_admissions = [a for a in active_admissions if a.status in [
        'Discharge In Progress', 'Awaiting Departmental Clearance', 'Ready for Final Discharge'
    ]]

    # Nursing tasks assigned or pending
    nursing_tasks = DepartmentTask.query.filter_by(department='Nursing')\
        .join(Admission)\
        .filter(Admission.status != 'Discharged')\
        .filter((DepartmentTask.assigned_to_user_id == nurse_id) | (Admission.assigned_nurse_id == nurse_id))\
        .order_by(DepartmentTask.status.desc(), DepartmentTask.created_at.desc()).all()

    pending_tasks_count = sum(1 for t in nursing_tasks if t.status in ['Pending', 'In Progress'])
    completed_tasks_count = sum(1 for t in nursing_tasks if t.status == 'Completed')
    blocked_tasks_count = sum(1 for t in nursing_tasks if t.status == 'Blocked')

    return render_template(
        'nurse_dashboard.html',
        active_admissions=active_admissions,
        discharge_admissions=discharge_admissions,
        nursing_tasks=nursing_tasks,
        pending_count=pending_tasks_count,
        completed_count=completed_tasks_count,
        blocked_count=blocked_tasks_count
    )

@nurse_bp.route('/discharge/<int:admission_id>')
@role_required(['nurse', 'admin'])
def discharge_tasks(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    coordination = admission.discharge_coordination
    if not coordination:
        flash('Discharge has not been initiated by the physician yet.', 'info')
        return redirect(url_for('nurse.dashboard'))

    tasks = DepartmentTask.query.filter_by(
        discharge_coordination_id=coordination.id,
        department='Nursing'
    ).all()
    communications = admission.communication_logs.order_by(CommunicationLog.created_at.desc()).all()

    return render_template(
        'nurse_discharge_detail.html',
        admission=admission,
        coordination=coordination,
        tasks=tasks,
        communications=communications
    )

@nurse_bp.route('/task/<int:task_id>/update', methods=['POST'])
@role_required(['nurse', 'admin'])
def update_task(task_id):
    task = DepartmentTask.query.get_or_404(task_id)
    if task.department != 'Nursing' and g.current_user.role != 'admin':
        flash('You are only authorized to update Nursing department tasks.', 'danger')
        return redirect(url_for('nurse.dashboard'))

    new_status = request.form.get('status', '').strip()
    remarks = request.form.get('remarks', '').strip()
    blocked_reason = request.form.get('blocked_reason', '').strip()

    try:
        DischargeService.update_task_status(
            task_id=task.id,
            new_status=new_status,
            user=g.current_user,
            remarks=remarks,
            blocked_reason=blocked_reason
        )
        flash(f"Task '{task.title}' updated to {new_status}.", 'success')
    except Exception as e:
        flash(f"Error updating task: {str(e)}", 'danger')

    return redirect(url_for('nurse.discharge_tasks', admission_id=task.admission_id))
