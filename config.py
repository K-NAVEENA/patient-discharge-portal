import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'patient-discharge-portal-dev-key-9823471029384'
    
    # Database connection string
    # Supports Render PostgreSQL, external MySQL, or SQLite fallback
    raw_db_url = os.environ.get('DATABASE_URL')
    
    # If running on Render, ignore localhost DB from committed .env
    if os.environ.get('RENDER') and raw_db_url and ('@localhost' in raw_db_url or '@127.0.0.1' in raw_db_url):
        raw_db_url = None

    if raw_db_url:
        # Render PostgreSQL uses postgres:// which SQLAlchemy deprecated in favor of postgresql://
        if raw_db_url.startswith('postgres://'):
            raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = raw_db_url
    elif os.environ.get('RENDER'):
        # On Render without an external database attached, use persistent SQLite instance
        basedir = os.path.abspath(os.path.dirname(__file__))
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'patient_discharge.db')
    else:
        # Standard local MySQL development
        SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost:3306/patient_discharge_db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Session Security
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = True if os.environ.get('RENDER') else False

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
