from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User
from models.patient import Patient
from models.room import Room
from models.admission import Admission
from models.discharge import DischargeCoordination
from models.task import DepartmentTask
from models.communication import CommunicationLog
from models.notification import Notification
from models.billing import BillingAccount, BillingItem, Payment
from models.audit import AuditEvent

__all__ = [
    'db',
    'User',
    'Patient',
    'Room',
    'Admission',
    'DischargeCoordination',
    'DepartmentTask',
    'CommunicationLog',
    'Notification',
    'BillingAccount',
    'BillingItem',
    'Payment',
    'AuditEvent',
]
