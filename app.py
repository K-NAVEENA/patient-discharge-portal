import os
import click
from datetime import datetime
from flask import Flask, render_template, session, g
from config import Config
from models import db, User, Notification
from routes import (
    auth_bp, admin_bp, doctor_bp, nurse_bp,
    pharmacy_bp, laboratory_bp, patient_bp,
    notifications_bp, communication_bp, billing_bp
)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Auto-initialize database tables and demo seed data on cloud/Render environments
    if os.environ.get('RENDER'):
        with app.app_context():
            try:
                db.create_all()
                if not User.query.filter_by(username='admin').first():
                    from database.seed import seed_database
                    seed_database()
            except Exception as e:
                app.logger.warning(f"Cloud auto-init note: {e}")

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(nurse_bp)
    app.register_blueprint(pharmacy_bp)
    app.register_blueprint(laboratory_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(communication_bp)
    app.register_blueprint(billing_bp)

    @app.before_request
    def load_logged_in_user():
        user_id = session.get('user_id')
        if user_id is None:
            g.current_user = None
        else:
            g.current_user = User.query.get(user_id)

    @app.context_processor
    def inject_global_data():
        unread_notifications_count = 0
        if g.current_user:
            unread_notifications_count = Notification.query.filter_by(
                recipient_user_id=g.current_user.id,
                is_read=False
            ).count()
        return {
            'current_user': g.current_user,
            'unread_notifications_count': unread_notifications_count,
            'now': datetime.utcnow()
        }

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('error.html', error_code=403, error_message="Access Forbidden: You lack required clearance for this clinical resource."), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error_code=404, error_message="Page Not Found: The requested portal resource does not exist."), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', error_code=500, error_message="Internal Server Error: A clinical system transaction failed. Please check logs."), 500

    # Custom CLI commands
    @app.cli.command("init-db")
    def init_db_command():
        """Creates all database tables."""
        with app.app_context():
            db.create_all()
            click.echo("Initialized database tables successfully.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt="Admin username", default="admin", help="Admin username")
    @click.option("--email", prompt="Admin email", default="admin@hospital.local", help="Admin email")
    @click.option("--password", prompt="Admin password", hide_input=True, confirmation_prompt=True, help="Admin password")
    @click.option("--name", prompt="Full name", default="System Administrator", help="Admin full name")
    def create_admin_command(username, email, password, name):
        """Creates or resets an administrator account."""
        with app.app_context():
            db.create_all()
            existing = User.query.filter((User.username == username) | (User.email == email)).first()
            if existing:
                existing.username = username
                existing.email = email
                existing.full_name = name
                existing.role = 'admin'
                existing.department = 'Administration'
                existing.approval_status = 'approved'
                existing.is_active = True
                existing.set_password(password)
                click.echo(f"Updated existing admin account '{username}'.")
            else:
                admin_user = User(
                    username=username,
                    email=email,
                    full_name=name,
                    role='admin',
                    department='Administration',
                    approval_status='approved',
                    is_active=True
                )
                admin_user.set_password(password)
                db.session.add(admin_user)
                click.echo(f"Created new admin account '{username}'.")
            db.session.commit()

    @app.cli.command("seed-db")
    def seed_db_command():
        """Populates database with synthetic demonstration records."""
        from database.seed import seed_database
        with app.app_context():
            seed_database()
            click.echo("Seeded demonstration database successfully.")

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)
