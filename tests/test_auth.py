import pytest
from flask import session
from models import User

def test_login_successful(client, sample_data):
    """Verify login with correct credentials redirects to role dashboard."""
    resp = client.post('/login', data={
        'login_id': 'admin',
        'password': 'Admin@123'
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.location.endswith('/dashboard') or resp.location.endswith('/admin/dashboard')

def test_login_invalid_password(client, sample_data):
    """Verify login fails with wrong password."""
    resp = client.post('/login', data={
        'login_id': 'admin',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Invalid username/email or password" in resp.data

def test_staff_registration_creates_pending_approval(client, app):
    """Verify staff public registration creates pending approval account."""
    resp = client.post('/register', data={
        'full_name': 'Dr. Alan Turing',
        'username': 'dr_alan',
        'email': 'alan@hospital.test',
        'phone': '555-8888',
        'role': 'doctor',
        'department': 'Neurology',
        'employee_id': 'DOC-777',
        'qualification': 'MD, PhD',
        'password': 'SecurePassword123',
        'confirm_password': 'SecurePassword123'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Registration submitted successfully" in resp.data

    with app.app_context():
        user = User.query.filter_by(username='dr_alan').first()
        assert user is not None
        assert user.approval_status == 'pending'
        assert user.role == 'doctor'

def test_pending_staff_cannot_login(client, app, sample_data):
    """Verify pending staff are blocked from logging in."""
    with app.app_context():
        pending_user = User(
            username='pending_nurse',
            email='pending@hospital.test',
            full_name='Pending Nurse',
            role='nurse',
            approval_status='pending',
            is_active=True
        )
        pending_user.set_password('Nurse@123')
        from models import db
        db.session.add(pending_user)
        db.session.commit()

    resp = client.post('/login', data={
        'login_id': 'pending_nurse',
        'password': 'Nurse@123'
    }, follow_redirects=True)
    assert b"Your registration is pending approval" in resp.data

def test_admin_cannot_be_created_via_public_registration(client):
    """Verify public registration rejects requested role 'admin'."""
    resp = client.post('/register', data={
        'full_name': 'Fake Admin',
        'username': 'fake_admin',
        'email': 'fake@hospital.test',
        'role': 'admin',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert b"Public registration cannot create administrator accounts" in resp.data

def test_role_based_access_control(client, sample_data):
    """Verify non-admin staff cannot access administrative endpoints."""
    # Login as nurse
    client.post('/login', data={'login_id': 'nurse_test', 'password': 'Nurse@123'})
    resp = client.get('/admin/dashboard', follow_redirects=True)
    assert b"Access denied: You do not have permission" in resp.data

def test_welcome_page_content_and_navigation(client):
    """Verify welcome page renders with required CareFlow branding, badge, and login action."""
    resp = client.get('/welcome')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert "CareFlow" in html
    assert "INTER-DEPARTMENTAL COMMUNICATION & WORKFLOW AUTOMATION" in html
    assert "Patient Discharge Coordination Portal" in html
    assert "Continue to Login" in html
    assert "/login" in html

def test_root_redirects_to_welcome_page(client):
    """Verify root / redirects unauthenticated visitors to /welcome."""
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code == 302
    assert resp.location.endswith('/welcome')

def test_login_page_removes_quick_demo_accounts(client):
    """Verify login page does not contain the Quick Demo Accounts section or demo account names."""
    resp = client.get('/login')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert "Quick Demo Accounts" not in html
    assert "admin: admin" not in html.lower()
    assert "dr_smith" not in html
    assert "nurse_emma" not in html
    assert "pharm_lisa" not in html
    assert "lab_robert" not in html
    assert "eleanor_vance" not in html

