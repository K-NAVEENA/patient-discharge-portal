import pytest
from models import db, Admission, Patient, User

def test_patient_can_only_access_own_records(client, sample_data):
    """Verify authenticated patient can view their own dashboard and not other patients."""
    # Login as patient
    client.post('/login', data={'login_id': 'pat_test', 'password': 'Patient@123'})

    resp = client.get('/patient/dashboard')
    assert resp.status_code == 200
    assert b"Welcome, John Doe" in resp.data
    assert b"PID-2026-9001" in resp.data

    # Attempt to access doctor dashboard
    resp = client.get('/doctor/dashboard', follow_redirects=True)
    assert b"Access denied: You do not have permission" in resp.data

    # Attempt to access admin dashboard
    resp = client.get('/admin/dashboard', follow_redirects=True)
    assert b"Access denied: You do not have permission" in resp.data
