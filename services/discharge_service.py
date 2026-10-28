import uuid
from datetime import datetime
from models import (
    db, Admission, DischargeCoordination, DepartmentTask,
    CommunicationLog, Room, AuditEvent, User
)
from services.notification_service import NotificationService
from services.billing_service import BillingService

class DischargeService:
    @staticmethod
    def calculate_discharge_readiness(admission_id):
        """
        Centralized discharge readiness engine.
        Evaluates clinical readiness, required departmental clearances, and task states.
        Enforces that NO required task remains pending, in progress, or blocked.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            return None

        coordination = DischargeCoordination.query.filter_by(admission_id=admission.id).first()
        if not coordination:
            return None

        # Do not alter finalized discharged records
        if coordination.is_finalized or admission.status == 'Discharged':
            return {
                'is_ready': False,
                'is_finalized': True,
                'status': 'Discharged',
                'clinical_ready': coordination.clinical_readiness_approved,
                'nursing_cleared': coordination.nursing_cleared,
                'pharmacy_cleared': coordination.pharmacy_cleared,
                'laboratory_cleared': coordination.laboratory_cleared,
                'blocked_tasks': []
            }

        tasks = DepartmentTask.query.filter_by(discharge_coordination_id=coordination.id).all()

        nursing_tasks = [t for t in tasks if t.department == 'Nursing']
        pharmacy_tasks = [t for t in tasks if t.department == 'Pharmacy']
        lab_tasks = [t for t in tasks if t.department == 'Laboratory']

        blocked_tasks = [t for t in tasks if t.status == 'Blocked']

        # 1. Nursing clearance check
        if coordination.requires_nursing:
            if nursing_tasks and all(t.status == 'Completed' for t in nursing_tasks):
                coordination.nursing_cleared = True
                if not coordination.nursing_cleared_at:
                    coordination.nursing_cleared_at = datetime.utcnow()
            else:
                coordination.nursing_cleared = False
                coordination.nursing_cleared_at = None
        else:
            coordination.nursing_cleared = True

        # 2. Pharmacy clearance check
        if coordination.requires_pharmacy:
            if pharmacy_tasks and all(t.status == 'Completed' for t in pharmacy_tasks):
                coordination.pharmacy_cleared = True
                if not coordination.pharmacy_cleared_at:
                    coordination.pharmacy_cleared_at = datetime.utcnow()
            else:
                coordination.pharmacy_cleared = False
                coordination.pharmacy_cleared_at = None
        else:
            coordination.pharmacy_cleared = True

        # 3. Laboratory clearance check
        if coordination.requires_laboratory:
            if lab_tasks and all(t.status == 'Completed' for t in lab_tasks):
                coordination.laboratory_cleared = True
                if not coordination.laboratory_cleared_at:
                    coordination.laboratory_cleared_at = datetime.utcnow()
            else:
                coordination.laboratory_cleared = False
                coordination.laboratory_cleared_at = None
        else:
            coordination.laboratory_cleared = True

        # 4. Total Readiness Evaluation
        has_blocked_tasks = len(blocked_tasks) > 0
        all_required_cleared = (
            coordination.nursing_cleared and
            coordination.pharmacy_cleared and
            coordination.laboratory_cleared
        )

        previous_readiness = coordination.is_ready_for_discharge
        is_ready = bool(
            coordination.clinical_readiness_approved and
            all_required_cleared and
            not has_blocked_tasks
        )

        coordination.is_ready_for_discharge = is_ready
        coordination.ready_calculated_at = datetime.utcnow()

        # Update Admission status
        if is_ready:
            admission.status = 'Ready for Final Discharge'
            if not previous_readiness:
                # Notify administrator that patient is ready for final discharge
                NotificationService.notify_admins(
                    event_type='ready_for_discharge',
                    title='Patient Ready for Final Discharge',
                    message=f"Patient {admission.patient.full_name} ({admission.patient.patient_id}) has received all departmental clearances and is ready for final discharge.",
                    link_url=f"/admin/discharge/{admission.id}"
                )
                # Also notify doctor
                NotificationService.create_notification(
                    recipient_user_id=admission.admitting_doctor_id,
                    event_type='ready_for_discharge',
                    title='Patient Ready for Final Discharge',
                    message=f"All clearances completed for {admission.patient.full_name}.",
                    link_url=f"/doctor/patient/{admission.id}"
                )
        elif coordination.clinical_readiness_approved:
            admission.status = 'Awaiting Departmental Clearance'
        else:
            admission.status = 'Discharge In Progress'

        db.session.flush()

        return {
            'is_ready': is_ready,
            'status': admission.status,
            'clinical_ready': coordination.clinical_readiness_approved,
            'nursing_cleared': coordination.nursing_cleared,
            'pharmacy_cleared': coordination.pharmacy_cleared,
            'laboratory_cleared': coordination.laboratory_cleared,
            'blocked_tasks': [t.to_dict() for t in blocked_tasks]
        }

    @staticmethod
    def initiate_discharge(admission_id, doctor_user, clinical_notes, follow_up_instructions,
                           requires_nursing=True, requires_pharmacy=True, requires_laboratory=False):
        """
        Doctor initiates clinical discharge readiness.
        Generates departmental coordination record and specific workflow tasks.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            raise ValueError("Admission not found")

        if admission.status == 'Discharged':
            raise ValueError("Patient has already been discharged")

        coordination = DischargeCoordination.query.filter_by(admission_id=admission.id).first()
        if not coordination:
            coordination = DischargeCoordination(
                admission_id=admission.id,
                initiated_by_doctor_id=doctor_user.id,
                initiated_at=datetime.utcnow()
            )
            db.session.add(coordination)
            db.session.flush()

        coordination.clinical_readiness_approved = True
        coordination.clinical_notes = clinical_notes
        coordination.follow_up_instructions = follow_up_instructions
        coordination.requires_nursing = requires_nursing
        coordination.requires_pharmacy = requires_pharmacy
        coordination.requires_laboratory = requires_laboratory
        admission.status = 'Awaiting Departmental Clearance'

        # Generate Departmental Tasks if not already present
        # 1. Nursing Tasks
        if requires_nursing:
            existing_nursing = DepartmentTask.query.filter_by(
                discharge_coordination_id=coordination.id,
                department='Nursing'
            ).first()
            if not existing_nursing:
                nursing_items = [
                    ("Discharge Vitals & Clinical Assessment", "Record final stable vital signs and assess mobility"),
                    ("Nursing Care Discontinuation", "Safely remove IV cannulas, urinary catheters, or dressings"),
                    ("Discharge Counseling & Belongings", "Explain wound care/home care instructions and return patient valuables")
                ]
                for title, desc in nursing_items:
                    task = DepartmentTask(
                        task_code=f"TSK-NUR-{uuid.uuid4().hex[:6].upper()}",
                        admission_id=admission.id,
                        discharge_coordination_id=coordination.id,
                        department='Nursing',
                        title=title,
                        description=desc,
                        assigned_to_user_id=admission.assigned_nurse_id,
                        status='Pending'
                    )
                    db.session.add(task)

                # Notify assigned nurse
                NotificationService.create_notification(
                    recipient_user_id=admission.assigned_nurse_id,
                    event_type='task_created',
                    title='Nursing Discharge Tasks Assigned',
                    message=f"Discharge tasks generated for patient {admission.patient.full_name} ({admission.room.room_number})",
                    link_url=f"/nurse/discharge/{admission.id}"
                )

        # 2. Pharmacy Tasks
        if requires_pharmacy:
            existing_pharm = DepartmentTask.query.filter_by(
                discharge_coordination_id=coordination.id,
                department='Pharmacy'
            ).first()
            if not existing_pharm:
                pharm_items = [
                    ("Medication Reconciliation & Verification", "Verify discharge medication orders and check contraindications"),
                    ("Prescription Dispensing & Patient Counseling", "Package discharge medications and provide dosage instructions")
                ]
                for title, desc in pharm_items:
                    task = DepartmentTask(
                        task_code=f"TSK-PHM-{uuid.uuid4().hex[:6].upper()}",
                        admission_id=admission.id,
                        discharge_coordination_id=coordination.id,
                        department='Pharmacy',
                        title=title,
                        description=desc,
                        status='Pending'
                    )
                    db.session.add(task)

                # Notify pharmacy staff
                NotificationService.notify_department(
                    department='Pharmacy',
                    event_type='task_created',
                    title='New Pharmacy Discharge Clearance Request',
                    message=f"Discharge medications reconciliation requested for {admission.patient.full_name}",
                    link_url=f"/pharmacy/discharge/{admission.id}"
                )

        # 3. Laboratory Tasks (Only if clinically required!)
        if requires_laboratory:
            existing_lab = DepartmentTask.query.filter_by(
                discharge_coordination_id=coordination.id,
                department='Laboratory'
            ).first()
            if not existing_lab:
                lab_task = DepartmentTask(
                    task_code=f"TSK-LAB-{uuid.uuid4().hex[:6].upper()}",
                    admission_id=admission.id,
                    discharge_coordination_id=coordination.id,
                    department='Laboratory',
                    title="Diagnostic Results Sign-Off & Clearance",
                    description="Confirm all ordered blood panels, cultures, or radiology investigations are finalized",
                    status='Pending'
                )
                db.session.add(lab_task)

                # Notify lab staff
                NotificationService.notify_department(
                    department='Laboratory',
                    event_type='task_created',
                    title='Laboratory Clearance Required',
                    message=f"Laboratory test sign-off requested for {admission.patient.full_name}",
                    link_url=f"/laboratory/discharge/{admission.id}"
                )

        # Log Communication
        comm = CommunicationLog(
            patient_id=admission.patient_id,
            admission_id=admission.id,
            discharge_coordination_id=coordination.id,
            sender_id=doctor_user.id,
            sender_role='doctor',
            source_department='Medical Staff',
            target_department='All Departments',
            message=f"Doctor {doctor_user.full_name} initiated discharge coordination: '{clinical_notes}'",
            log_type='clearance'
        )
        db.session.add(comm)

        # Sync current room charges to billing
        BillingService.sync_room_charges(admission, recorded_by_user_id=doctor_user.id)

        db.session.commit()
        DischargeService.calculate_discharge_readiness(admission.id)
        db.session.commit()
        return coordination

    @staticmethod
    def update_task_status(task_id, new_status, user, remarks=None, blocked_reason=None):
        """
        Updates a departmental task with audit log and communication broadcast.
        Recalculates discharge readiness automatically.
        """
        task = DepartmentTask.query.get(task_id)
        if not task:
            raise ValueError("Task not found")

        valid_statuses = ['Pending', 'In Progress', 'Completed', 'Blocked']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}")

        if new_status == 'Blocked' and not blocked_reason:
            raise ValueError("A clear reason is mandatory when marking a task as Blocked")

        old_status = task.status
        task.status = new_status
        task.remarks = remarks or task.remarks

        if new_status == 'Completed':
            task.completed_by_user_id = user.id
            task.completed_at = datetime.utcnow()
            task.blocked_reason = None
        elif new_status == 'Blocked':
            task.blocked_reason = blocked_reason
            task.completed_at = None
            task.completed_by_user_id = None
        else:
            task.completed_at = None

        # Log communication entry
        log_type = 'alert' if new_status == 'Blocked' else ('clearance' if new_status == 'Completed' else 'status_change')
        msg = f"Task '{task.title}' updated from {old_status} to {new_status} by {user.full_name} ({user.role})."
        if new_status == 'Blocked':
            msg += f" Reason: {blocked_reason}"
        if remarks:
            msg += f" Remarks: {remarks}"

        comm = CommunicationLog(
            patient_id=task.admission.patient_id,
            admission_id=task.admission_id,
            discharge_coordination_id=task.discharge_coordination_id,
            task_id=task.id,
            sender_id=user.id,
            sender_role=user.role,
            source_department=task.department,
            target_department='All Staff',
            message=msg,
            log_type=log_type
        )
        db.session.add(comm)

        # Notify doctor and admin if blocked
        if new_status == 'Blocked':
            NotificationService.create_notification(
                recipient_user_id=task.admission.admitting_doctor_id,
                event_type='task_blocked',
                title=f"Discharge Task Blocked: {task.title}",
                message=f"{task.department} task blocked for {task.admission.patient.full_name}. Reason: {blocked_reason}",
                link_url=f"/doctor/patient/{task.admission_id}"
            )
            NotificationService.notify_admins(
                event_type='task_blocked',
                title=f"Discharge Task Blocked: {task.title}",
                message=f"{task.department} task blocked for {task.admission.patient.full_name}: {blocked_reason}",
                link_url=f"/admin/discharge/{task.admission_id}"
            )

        db.session.flush()
        # Recalculate readiness
        DischargeService.calculate_discharge_readiness(task.admission_id)
        db.session.commit()
        return task

    @staticmethod
    def finalize_final_discharge(admission_id, admin_user, discharge_summary=None, release_room=True):
        """
        Final discharge workflow executed by Administrator.
        Revalidates clinical and departmental conditions.
        Ensures idempotency (no duplicate finalization).
        Updates records, releases room, notifies patient & staff within an ACID transaction.
        """
        admission = Admission.query.get(admission_id)
        if not admission:
            raise ValueError("Admission record not found")

        if admission.status == 'Discharged':
            raise ValueError("This admission has already been finalized and discharged")

        coordination = DischargeCoordination.query.filter_by(admission_id=admission.id).first()
        if not coordination:
            raise ValueError("No discharge coordination record found for this admission")

        # Recalculate readiness to guarantee conditions
        readiness = DischargeService.calculate_discharge_readiness(admission_id)
        if not readiness['is_ready']:
            raise ValueError(
                "Patient cannot be discharged: One or more departmental clearances are incomplete or tasks are blocked."
            )

        now = datetime.utcnow()

        # Update Admission
        admission.status = 'Discharged'
        admission.discharge_date = now
        admission.discharged_by_user_id = admin_user.id
        admission.discharge_summary = discharge_summary or coordination.clinical_notes

        # Update Coordination
        coordination.is_finalized = True
        coordination.final_discharged_at = now
        coordination.final_discharged_by_id = admin_user.id

        # Update Room status
        room = admission.room
        if release_room and room:
            room.is_occupied = False
            room.current_patient_id = None
            room.current_admission_id = None

        # Finalize Billing: sync final room charges to actual discharge date/time
        billing_account = BillingService.sync_room_charges(admission, recorded_by_user_id=admin_user.id)
        billing_account.is_finalized = True

        # Audit event
        audit = AuditEvent(
            user_id=admin_user.id,
            action='FINAL_DISCHARGE',
            entity_type='Admission',
            entity_id=str(admission.id),
            details=f"Admin {admin_user.full_name} finalized discharge for patient {admission.patient.full_name} ({admission.admission_number}). Room {room.room_number if room else 'N/A'} released."
        )
        db.session.add(audit)

        # Communication Log
        comm = CommunicationLog(
            patient_id=admission.patient_id,
            admission_id=admission.id,
            discharge_coordination_id=coordination.id,
            sender_id=admin_user.id,
            sender_role='admin',
            source_department='Administration',
            target_department='All Staff',
            message=f"Final discharge approved and processed by {admin_user.full_name}. Patient {admission.patient.full_name} discharged successfully.",
            log_type='clearance'
        )
        db.session.add(comm)

        # Notify Patient if portal account exists
        if admission.patient.user_id:
            NotificationService.create_notification(
                recipient_user_id=admission.patient.user_id,
                event_type='discharge_finalized',
                title='Discharge Finalized',
                message="Your hospital discharge process has been finalized. You may view your summary and billing statement.",
                link_url='/patient/dashboard'
            )

        # Notify Doctor and Nurse
        NotificationService.create_notification(
            recipient_user_id=admission.admitting_doctor_id,
            event_type='discharge_finalized',
            title='Discharge Completed',
            message=f"Final discharge completed for your patient {admission.patient.full_name}.",
            link_url=f"/doctor/patient/{admission.id}"
        )
        NotificationService.create_notification(
            recipient_user_id=admission.assigned_nurse_id,
            event_type='discharge_finalized',
            title='Discharge Completed',
            message=f"Final discharge completed for patient {admission.patient.full_name}.",
            link_url=f"/nurse/discharge/{admission.id}"
        )

        db.session.commit()
        return admission
