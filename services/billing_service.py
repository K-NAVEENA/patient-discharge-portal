import uuid
from datetime import datetime
from models import db, BillingAccount, BillingItem, Payment, Admission, Room
from config import Config

class BillingService:
    @staticmethod
    def get_or_create_billing_account(admission):
        """Ensures an active billing account exists for this admission."""
        account = BillingAccount.query.filter_by(admission_id=admission.id).first()
        if not account:
            account = BillingAccount(
                admission_id=admission.id,
                patient_id=admission.patient_id,
                created_at=datetime.utcnow()
            )
            db.session.add(account)
            db.session.flush()
        return account

    @staticmethod
    def sync_room_charges(admission, recorded_by_user_id=None):
        """Calculates and updates room and daily hospital charges based on stay duration."""
        account = BillingService.get_or_create_billing_account(admission)
        room = admission.room
        if not room:
            return account

        stay_days = admission.length_of_stay_days
        room_rate = room.daily_rate

        # Sync Room Charge Item
        room_item = BillingItem.query.filter_by(
            billing_account_id=account.id,
            category='Room'
        ).first()

        room_desc = f"Room Charges - {room.ward} (Room {room.room_number}, {room.room_type}) for {stay_days} day(s)"
        total_room = round(stay_days * room_rate, 2)

        if room_item:
            room_item.description = room_desc
            room_item.unit_price = room_rate
            room_item.quantity = float(stay_days)
            room_item.total_price = total_room
        else:
            room_item = BillingItem(
                billing_account_id=account.id,
                category='Room',
                description=room_desc,
                unit_price=room_rate,
                quantity=float(stay_days),
                total_price=total_room,
                added_by_user_id=recorded_by_user_id,
                created_at=datetime.utcnow()
            )
            db.session.add(room_item)

        # Sync Routine Doctor Consultation
        consult_rate = Config.CONSULTATION_CHARGE_PER_DAY
        consult_item = BillingItem.query.filter_by(
            billing_account_id=account.id,
            category='Doctor Consultation'
        ).first()
        consult_desc = f"Doctor Inpatient Visit & Consultation ({stay_days} day(s))"
        total_consult = round(stay_days * consult_rate, 2)

        if consult_item:
            consult_item.description = consult_desc
            consult_item.unit_price = consult_rate
            consult_item.quantity = float(stay_days)
            consult_item.total_price = total_consult
        else:
            consult_item = BillingItem(
                billing_account_id=account.id,
                category='Doctor Consultation',
                description=consult_desc,
                unit_price=consult_rate,
                quantity=float(stay_days),
                total_price=total_consult,
                added_by_user_id=recorded_by_user_id,
                created_at=datetime.utcnow()
            )
            db.session.add(consult_item)

        # Sync Nursing Care
        nursing_rate = Config.NURSING_CARE_CHARGE_PER_DAY
        nursing_item = BillingItem.query.filter_by(
            billing_account_id=account.id,
            category='Nursing Care'
        ).first()
        nursing_desc = f"Round-the-clock Inpatient Nursing Care ({stay_days} day(s))"
        total_nursing = round(stay_days * nursing_rate, 2)

        if nursing_item:
            nursing_item.description = nursing_desc
            nursing_item.unit_price = nursing_rate
            nursing_item.quantity = float(stay_days)
            nursing_item.total_price = total_nursing
        else:
            nursing_item = BillingItem(
                billing_account_id=account.id,
                category='Nursing Care',
                description=nursing_desc,
                unit_price=nursing_rate,
                quantity=float(stay_days),
                total_price=total_nursing,
                added_by_user_id=recorded_by_user_id,
                created_at=datetime.utcnow()
            )
            db.session.add(nursing_item)

        db.session.flush()
        account.recalculate_totals()
        return account

    @staticmethod
    def add_billing_item(billing_account_id, category, description, unit_price, quantity, added_by_user_id=None):
        """Adds a specific billing line item (e.g. Pharmacy medicine, Laboratory test)."""
        account = BillingAccount.query.get(billing_account_id)
        if not account:
            raise ValueError("Billing account not found")

        total_price = round(unit_price * quantity, 2)
        item = BillingItem(
            billing_account_id=account.id,
            category=category,
            description=description,
            unit_price=unit_price,
            quantity=quantity,
            total_price=total_price,
            added_by_user_id=added_by_user_id,
            created_at=datetime.utcnow()
        )
        db.session.add(item)
        db.session.flush()
        account.recalculate_totals()
        return item

    @staticmethod
    def record_payment(billing_account_id, amount, payment_method, recorded_by_user_id, transaction_id=None, notes=None):
        """Records a patient or insurance payment against the billing account."""
        account = BillingAccount.query.get(billing_account_id)
        if not account:
            raise ValueError("Billing account not found")

        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero")

        ref_number = f"PAY-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        payment = Payment(
            billing_account_id=account.id,
            payment_reference=ref_number,
            amount=round(float(amount), 2),
            payment_method=payment_method,
            transaction_id=transaction_id,
            notes=notes,
            recorded_by_user_id=recorded_by_user_id,
            created_at=datetime.utcnow()
        )
        db.session.add(payment)
        db.session.flush()
        account.recalculate_totals()
        return payment

    @staticmethod
    def apply_discount(billing_account_id, discount_amount):
        """Applies an authorized hospital discount/adjustment."""
        account = BillingAccount.query.get(billing_account_id)
        if not account:
            raise ValueError("Billing account not found")
        account.discount_amount = max(0.0, float(discount_amount))
        account.recalculate_totals()
        return account
