from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models import db, User, Patient, AuditEvent
from services.notification_service import NotificationService

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Your account is deactivated or no longer exists.', 'danger')
            return redirect(url_for('auth.login'))
        if user.approval_status != 'approved':
            session.clear()
            flash('Your account is pending administrator approval or has been rejected.', 'warning')
            return redirect(url_for('auth.login'))
        if user.must_change_password and request.endpoint not in ['auth.change_password', 'auth.logout']:
            flash('Please change your temporary password before proceeding.', 'info')
            return redirect(url_for('auth.change_password'))
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if g.current_user.role not in allowed_roles:
                flash('Access denied: You do not have permission to view this page.', 'danger')
                return redirect(url_for('auth.role_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('auth.role_dashboard'))
    return redirect(url_for('auth.welcome'))

@auth_bp.route('/welcome')
def welcome():
    if 'user_id' in session:
        return redirect(url_for('auth.role_dashboard'))
    return render_template('welcome.html')

@auth_bp.route('/dashboard')
@login_required
def role_dashboard():
    role = g.current_user.role
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'doctor':
        return redirect(url_for('doctor.dashboard'))
    elif role == 'nurse':
        return redirect(url_for('nurse.dashboard'))
    elif role == 'pharmacy':
        return redirect(url_for('pharmacy.dashboard'))
    elif role == 'laboratory':
        return redirect(url_for('laboratory.dashboard'))
    elif role == 'patient':
        return redirect(url_for('patient.dashboard'))
    else:
        flash('Unrecognized role.', 'danger')
        return redirect(url_for('auth.logout'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('auth.role_dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')

        if not login_id or not password:
            flash('Please enter both identifier (username/email) and password.', 'danger')
            return render_template('login.html')

        user = User.query.filter(
            (User.username == login_id) | (User.email == login_id)
        ).first()

        if not user or not user.check_password(password):
            flash('Invalid username/email or password.', 'danger')
            return render_template('login.html')

        if not user.is_active:
            flash('Your account has been deactivated. Please contact an administrator.', 'danger')
            return render_template('login.html')

        if user.approval_status == 'pending':
            flash('Your registration is pending approval by the hospital administrator.', 'warning')
            return render_template('login.html')
        elif user.approval_status == 'rejected':
            flash('Your registration was rejected by the administrator. Contact hospital HR.', 'danger')
            return render_template('login.html')

        # Authentication Successful
        session.clear()
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_name'] = user.full_name
        session.permanent = True

        # Audit Event
        audit = AuditEvent(
            user_id=user.id,
            action='USER_LOGIN',
            entity_type='User',
            entity_id=str(user.id),
            details=f"User {user.username} ({user.role}) logged in successfully.",
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()

        if user.must_change_password:
            flash('Please change your temporary password to continue.', 'info')
            return redirect(url_for('auth.change_password'))

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        return redirect(url_for('auth.role_dashboard'))

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        requested_role = request.form.get('role', '').strip().lower()
        employee_id = request.form.get('employee_id', '').strip()
        qualification = request.form.get('qualification', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-side validation
        if requested_role not in ['doctor', 'nurse', 'pharmacy', 'laboratory']:
            flash('Invalid role selected. Public registration cannot create administrator accounts.', 'danger')
            return render_template('register.html')

        if not full_name or not username or not email or not password:
            flash('Full name, username, email, and password are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username is already taken.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'danger')
            return render_template('register.html')

        new_user = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=phone,
            department=department or requested_role.title(),
            role=requested_role,
            employee_id=employee_id,
            qualification=qualification,
            approval_status='pending', # Crucial: pending administrator approval
            is_active=True,
            must_change_password=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        # Notify administrator
        NotificationService.notify_admins(
            event_type='staff_registered',
            title='New Staff Registration Request',
            message=f"{full_name} registered as {requested_role.title()} ({department or requested_role.title()}). Pending your approval.",
            link_url='/admin/staff'
        )

        audit = AuditEvent(
            user_id=new_user.id,
            action='STAFF_REGISTER_SUBMITTED',
            entity_type='User',
            entity_id=str(new_user.id),
            details=f"Staff account registration submitted for {username} as {requested_role}."
        )
        db.session.add(audit)
        db.session.commit()

        flash('Registration submitted successfully! Your account is pending administrator approval before you can log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not user.check_password(old_password):
            flash('Current/temporary password is incorrect.', 'danger')
            return render_template('change_password.html')

        if len(new_password) < 6:
            flash('New password must be at least 6 characters.', 'danger')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return render_template('change_password.html')

        user.set_password(new_password)
        user.must_change_password = False
        db.session.commit()

        flash('Password updated successfully! Welcome to the portal.', 'success')
        return redirect(url_for('auth.role_dashboard'))

    return render_template('change_password.html')

@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        audit = AuditEvent(
            user_id=user_id,
            action='USER_LOGOUT',
            entity_type='User',
            entity_id=str(user_id),
            details="User logged out."
        )
        db.session.add(audit)
        db.session.commit()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
