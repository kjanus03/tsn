from flask_socketio import emit, join_room
from flask_login import current_user
from .extensions import socketio, db
from datetime import datetime
from .models import Notification

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        # Join a room specific to this user
        room = f'user_{current_user.id}'
        join_room(room)
        print(f"User {current_user.username} connected to Socket.IO and joined room {room}")

def send_notification(user_id, message, notification_type='default', link=None):
    print(f"Preparing notification for user {user_id}")
    print(f"Message: {message}")
    print(f"Type: {notification_type}")
    print(f"Link: {link}")
    
    # Create notification in database
    notification = Notification(
        user_id=user_id,
        message=message,
        notification_type=notification_type,
        link=link,
        timestamp=datetime.utcnow()
    )
    
    try:
        db.session.add(notification)
        db.session.commit()
        
        notification_data = notification.to_dict()
        
        room = f'user_{user_id}'
        print(f"Emitting notification to room: {room}")
        print(f"Notification data: {notification_data}")
        
        # Emit to the user's specific room
        emit('new_notification', notification_data, room=room)
        print(f"Notification sent to room {room}")
    except Exception as e:
        print(f"Error creating notification: {str(e)}")
        db.session.rollback() 