from flask import Blueprint, render_template, redirect, url_for, flash, g
from models import db, Patient, Admission, DischargeCoordination, BillingAccount
from routes.auth import role_required
from services.billing_service import BillingService

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

@patient_bp.route('/dashboard')
@role_required('patient')
def dashboard():
    # Only view authenticated patient's profile
    patient = Patient.query.filter_by(user_id=g.current_user.id).first()
    if not patient:
        flash('No patient clinical profile linked to your user account.', 'warning')
        return render_template('patient_dashboard.html', patient=None, current_admission=None)

    current_admission = patient.current_admission
    past_admissions = patient.admissions.filter(Admission.status == 'Discharged').all()

    coordination = current_admission.discharge_coordination if current_admission else None
    billing_account = None

    if current_admission:
        # Sync current room charges to reflect real stay
        billing_account = BillingService.sync_room_charges(current_admission)
    elif past_admissions:
        billing_account = past_admissions[0].billing_account

    return render_template(
        'patient_dashboard.html',
        patient=patient,
        current_admission=current_admission,
        past_admissions=past_admissions,
        coordination=coordination,
        billing_account=billing_account
    )
