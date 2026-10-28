from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db, DepartmentTask, Admission, CommunicationLog, DischargeCoordination, BillingAccount
from routes.auth import role_required
from services.discharge_service import DischargeService
from services.billing_service import BillingService

laboratory_bp = Blueprint('laboratory', __name__, url_prefix='/laboratory')

@laboratory_bp.route('/dashboard')
@role_required(['laboratory', 'admin'])
def dashboard():
    lab_tasks = DepartmentTask.query.filter_by(department='Laboratory')\
        .join(Admission)\
        .filter(Admission.status != 'Discharged')\
        .order_by(DepartmentTask.status.desc(), DepartmentTask.created_at.desc()).all()

    pending_count = sum(1 for t in lab_tasks if t.status in ['Pending', 'In Progress'])
    completed_count = sum(1 for t in lab_tasks if t.status == 'Completed')
    blocked_count = sum(1 for t in lab_tasks if t.status == 'Blocked')

    admission_ids = list({t.admission_id for t in lab_tasks})
    admissions_queue = Admission.query.filter(Admission.id.in_(admission_ids)).all() if admission_ids else []

    return render_template(
        'laboratory_dashboard.html',
        tasks=lab_tasks,
        admissions_queue=admissions_queue,
        pending_count=pending_count,
        completed_count=completed_count,
        blocked_count=blocked_count
    )

@laboratory_bp.route('/discharge/<int:admission_id>')
@role_required(['laboratory', 'admin'])
def discharge_tasks(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    coordination = admission.discharge_coordination
    if not coordination:
        flash('Discharge coordination record not found.', 'warning')
        return redirect(url_for('laboratory.dashboard'))

    tasks = DepartmentTask.query.filter_by(
        discharge_coordination_id=coordination.id,
        department='Laboratory'
    ).all()
    communications = admission.communication_logs.order_by(CommunicationLog.created_at.desc()).all()
    billing_account = BillingAccount.query.filter_by(admission_id=admission.id).first()

    return render_template(
        'laboratory_discharge_detail.html',
        admission=admission,
        coordination=coordination,
        tasks=tasks,
        communications=communications,
        billing_account=billing_account
    )

@laboratory_bp.route('/task/<int:task_id>/update', methods=['POST'])
@role_required(['laboratory', 'admin'])
def update_task(task_id):
    task = DepartmentTask.query.get_or_404(task_id)
    if task.department != 'Laboratory' and g.current_user.role != 'admin':
        flash('You are only authorized to update Laboratory tasks.', 'danger')
        return redirect(url_for('laboratory.dashboard'))

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
        flash(f"Laboratory task '{task.title}' updated to {new_status}.", 'success')
    except Exception as e:
        flash(f"Error updating task: {str(e)}", 'danger')

    return redirect(url_for('laboratory.discharge_tasks', admission_id=task.admission_id))

@laboratory_bp.route('/billing/<int:admission_id>/add-test', methods=['POST'])
@role_required(['laboratory', 'admin'])
def add_test_charge(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    test_name = request.form.get('test_name', '').strip()
    unit_price = float(request.form.get('unit_price', 0.0))
    quantity = float(request.form.get('quantity', 1.0))

    if not test_name or unit_price <= 0:
        flash('Valid test name and positive price are required.', 'danger')
        return redirect(url_for('laboratory.discharge_tasks', admission_id=admission.id))

    account = BillingService.get_or_create_billing_account(admission)
    BillingService.add_billing_item(
        billing_account_id=account.id,
        category='Laboratory',
        description=f"Lab Investigation: {test_name}",
        unit_price=unit_price,
        quantity=quantity,
        added_by_user_id=g.current_user.id
    )
    flash(f"Laboratory charge for '{test_name}' added to patient bill.", 'success')
    return redirect(url_for('laboratory.discharge_tasks', admission_id=admission.id))
