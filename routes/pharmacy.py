from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db, DepartmentTask, Admission, CommunicationLog, DischargeCoordination, BillingAccount
from routes.auth import role_required
from services.discharge_service import DischargeService
from services.billing_service import BillingService

pharmacy_bp = Blueprint('pharmacy', __name__, url_prefix='/pharmacy')

@pharmacy_bp.route('/dashboard')
@role_required(['pharmacy', 'admin'])
def dashboard():
    # Find all admissions with pending or active pharmacy tasks
    pharmacy_tasks = DepartmentTask.query.filter_by(department='Pharmacy')\
        .join(Admission)\
        .filter(Admission.status != 'Discharged')\
        .order_by(DepartmentTask.status.desc(), DepartmentTask.created_at.desc()).all()

    pending_count = sum(1 for t in pharmacy_tasks if t.status in ['Pending', 'In Progress'])
    completed_count = sum(1 for t in pharmacy_tasks if t.status == 'Completed')
    blocked_count = sum(1 for t in pharmacy_tasks if t.status == 'Blocked')

    # Distinct admissions in queue
    admission_ids = list({t.admission_id for t in pharmacy_tasks})
    admissions_queue = Admission.query.filter(Admission.id.in_(admission_ids)).all() if admission_ids else []

    return render_template(
        'pharmacy_dashboard.html',
        tasks=pharmacy_tasks,
        admissions_queue=admissions_queue,
        pending_count=pending_count,
        completed_count=completed_count,
        blocked_count=blocked_count
    )

@pharmacy_bp.route('/discharge/<int:admission_id>')
@role_required(['pharmacy', 'admin'])
def discharge_tasks(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    coordination = admission.discharge_coordination
    if not coordination:
        flash('Discharge coordination record not found.', 'warning')
        return redirect(url_for('pharmacy.dashboard'))

    tasks = DepartmentTask.query.filter_by(
        discharge_coordination_id=coordination.id,
        department='Pharmacy'
    ).all()
    communications = admission.communication_logs.order_by(CommunicationLog.created_at.desc()).all()
    billing_account = BillingAccount.query.filter_by(admission_id=admission.id).first()

    return render_template(
        'pharmacy_discharge_detail.html',
        admission=admission,
        coordination=coordination,
        tasks=tasks,
        communications=communications,
        billing_account=billing_account
    )

@pharmacy_bp.route('/task/<int:task_id>/update', methods=['POST'])
@role_required(['pharmacy', 'admin'])
def update_task(task_id):
    task = DepartmentTask.query.get_or_404(task_id)
    if task.department != 'Pharmacy' and g.current_user.role != 'admin':
        flash('You are only authorized to update Pharmacy tasks.', 'danger')
        return redirect(url_for('pharmacy.dashboard'))

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
        flash(f"Pharmacy task '{task.title}' updated to {new_status}.", 'success')
    except Exception as e:
        flash(f"Error updating task: {str(e)}", 'danger')

    return redirect(url_for('pharmacy.discharge_tasks', admission_id=task.admission_id))

@pharmacy_bp.route('/billing/<int:admission_id>/add-medication', methods=['POST'])
@role_required(['pharmacy', 'admin'])
def add_medication_charge(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    med_name = request.form.get('med_name', '').strip()
    unit_price = float(request.form.get('unit_price', 0.0))
    quantity = float(request.form.get('quantity', 1.0))

    if not med_name or unit_price <= 0:
        flash('Valid medication name and positive price are required.', 'danger')
        return redirect(url_for('pharmacy.discharge_tasks', admission_id=admission.id))

    account = BillingService.get_or_create_billing_account(admission)
    BillingService.add_billing_item(
        billing_account_id=account.id,
        category='Pharmacy',
        description=f"Prescription Meds: {med_name}",
        unit_price=unit_price,
        quantity=quantity,
        added_by_user_id=g.current_user.id
    )
    flash(f"Medication charge for '{med_name}' added to patient bill.", 'success')
    return redirect(url_for('pharmacy.discharge_tasks', admission_id=admission.id))
