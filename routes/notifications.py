from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from models import db, Notification
from routes.auth import login_required

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/')
@login_required
def index():
    user_notifications = Notification.query.filter_by(recipient_user_id=g.current_user.id)\
        .order_by(Notification.created_at.desc()).limit(50).all()
    return render_template('notifications.html', notifications=user_notifications)

@notifications_bp.route('/api/unread')
@login_required
def get_unread_api():
    """Asynchronous polling endpoint for navbar notification badge."""
    unread_notifs = Notification.query.filter_by(
        recipient_user_id=g.current_user.id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()

    unread_count = Notification.query.filter_by(
        recipient_user_id=g.current_user.id,
        is_read=False
    ).count()

    return jsonify({
        'unread_count': unread_count,
        'notifications': [n.to_dict() for n in unread_notifs]
    })

@notifications_bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.recipient_user_id == g.current_user.id:
        notif.is_read = True
        db.session.commit()
    
    redirect_url = request.form.get('redirect_url')
    if redirect_url:
        return redirect(redirect_url)
    return jsonify({'success': True})

@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(
        recipient_user_id=g.current_user.id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('notifications.index'))
