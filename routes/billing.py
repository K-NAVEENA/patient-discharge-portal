from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db, Admission, BillingAccount, BillingItem, Payment, AuditEvent
from routes.auth import role_required
from services.billing_service import BillingService

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/<int:admission_id>')
@role_required(['admin', 'doctor', 'nurse', 'pharmacy'])
def account_detail(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    billing_account = BillingService.sync_room_charges(admission)
    items = billing_account.items.order_by(BillingItem.created_at.asc()).all()
    payments = billing_account.payments.order_by(Payment.created_at.desc()).all()

    return render_template(
        'billing.html',
        admission=admission,
        account=billing_account,
        items=items,
        payments=payments
    )

@billing_bp.route('/<int:admission_id>/add-item', methods=['POST'])
@role_required('admin')
def add_item(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    account = BillingService.get_or_create_billing_account(admission)

    if account.is_finalized:
        flash('Cannot add items to a finalized billing statement.', 'danger')
        return redirect(url_for('billing.account_detail', admission_id=admission.id))

    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    unit_price = float(request.form.get('unit_price', 0.0))
    quantity = float(request.form.get('quantity', 1.0))

    if not category or not description or unit_price < 0:
        flash('Invalid billing item details.', 'danger')
        return redirect(url_for('billing.account_detail', admission_id=admission.id))

    BillingService.add_billing_item(
        billing_account_id=account.id,
        category=category,
        description=description,
        unit_price=unit_price,
        quantity=quantity,
        added_by_user_id=g.current_user.id
    )

    audit = AuditEvent(
        user_id=g.current_user.id,
        action='BILLING_ITEM_ADDED',
        entity_type='BillingItem',
        entity_id=str(account.id),
        details=f"Added {category} charge: {description} (Qty: {quantity}, Rate: {unit_price})."
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"Line item '{description}' added to patient bill.", 'success')
    return redirect(url_for('billing.account_detail', admission_id=admission.id))

@billing_bp.route('/<int:admission_id>/payment', methods=['POST'])
@role_required('admin')
def record_payment(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    account = BillingService.get_or_create_billing_account(admission)

    amount = float(request.form.get('amount', 0.0))
    payment_method = request.form.get('payment_method', 'Cash').strip()
    transaction_id = request.form.get('transaction_id', '').strip()
    notes = request.form.get('notes', '').strip()

    if amount <= 0:
        flash('Payment amount must be greater than zero.', 'danger')
        return redirect(url_for('billing.account_detail', admission_id=admission.id))

    try:
        payment = BillingService.record_payment(
            billing_account_id=account.id,
            amount=amount,
            payment_method=payment_method,
            recorded_by_user_id=g.current_user.id,
            transaction_id=transaction_id,
            notes=notes
        )

        audit = AuditEvent(
            user_id=g.current_user.id,
            action='PAYMENT_RECORDED',
            entity_type='Payment',
            entity_id=str(payment.id),
            details=f"Payment of {amount} recorded ({payment_method}) - Ref: {payment.payment_reference}"
        )
        db.session.add(audit)
        db.session.commit()

        flash(f'Payment of ${amount:.2f} recorded successfully (Receipt Ref: {payment.payment_reference}).', 'success')
    except Exception as e:
        flash(f'Error recording payment: {str(e)}', 'danger')

    return redirect(url_for('billing.account_detail', admission_id=admission.id))

@billing_bp.route('/<int:admission_id>/discount', methods=['POST'])
@role_required('admin')
def apply_discount(admission_id):
    admission = Admission.query.get_or_404(admission_id)
    account = BillingService.get_or_create_billing_account(admission)

    if account.is_finalized:
        flash('Cannot adjust finalized billing statements.', 'danger')
        return redirect(url_for('billing.account_detail', admission_id=admission.id))

    discount = float(request.form.get('discount_amount', 0.0))
    BillingService.apply_discount(account.id, discount)
    db.session.commit()

    flash(f'Discount of ${discount:.2f} applied.', 'success')
    return redirect(url_for('billing.account_detail', admission_id=admission.id))
