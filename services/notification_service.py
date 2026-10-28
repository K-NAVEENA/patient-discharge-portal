from datetime import datetime
from models import db, Notification, User

class NotificationService:
    @staticmethod
    def create_notification(recipient_user_id, event_type, title, message, link_url=None):
        """Creates a persistent database notification for a specific user."""
        if not recipient_user_id:
            return None
        notification = Notification(
            recipient_user_id=recipient_user_id,
            event_type=event_type,
            title=title,
            message=message,
            link_url=link_url,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        return notification

    @staticmethod
    def notify_role(role, event_type, title, message, link_url=None):
        """Notifies all approved and active users with the given role."""
        users = User.query.filter_by(role=role, approval_status='approved', is_active=True).all()
        created = []
        for u in users:
            notif = NotificationService.create_notification(u.id, event_type, title, message, link_url)
            created.append(notif)
        return created

    @staticmethod
    def notify_department(department, event_type, title, message, link_url=None):
        """Notifies all approved active users in a given department or with matching role."""
        users = User.query.filter(
            (User.department == department) | (User.role == department.lower()),
            User.approval_status == 'approved',
            User.is_active == True
        ).all()
        created = []
        for u in users:
            notif = NotificationService.create_notification(u.id, event_type, title, message, link_url)
            created.append(notif)
        return created

    @staticmethod
    def notify_admins(event_type, title, message, link_url=None):
        """Notifies all active administrator accounts."""
        return NotificationService.notify_role('admin', event_type, title, message, link_url)
