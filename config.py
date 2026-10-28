import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'patient-discharge-portal-dev-key-9823471029384'
    
    # Database connection string - Defaults to standard MySQL localhost installation
    # Example: mysql+pymysql://root:password@localhost:3306/patient_discharge_db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:@localhost:3306/patient_discharge_db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Session Security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production

    # Hospital configurable rates (standard baseline)
    DEFAULT_ROOM_RATES = {
        'General Ward': 1200.0,
        'Semi-Private': 2500.0,
        'Private AC': 4500.0,
        'ICU': 8500.0,
        'Deluxe Suite': 6000.0
    }
    CONSULTATION_CHARGE_PER_DAY = 750.0
    NURSING_CARE_CHARGE_PER_DAY = 500.0
