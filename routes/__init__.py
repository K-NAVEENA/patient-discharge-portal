from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.doctor import doctor_bp
from routes.nurse import nurse_bp
from routes.pharmacy import pharmacy_bp
from routes.laboratory import laboratory_bp
from routes.patient import patient_bp
from routes.notifications import notifications_bp
from routes.communication import communication_bp
from routes.billing import billing_bp

__all__ = [
    'auth_bp',
    'admin_bp',
    'doctor_bp',
    'nurse_bp',
    'pharmacy_bp',
    'laboratory_bp',
    'patient_bp',
    'notifications_bp',
    'communication_bp',
    'billing_bp'
]
