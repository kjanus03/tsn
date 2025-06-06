import sys
print("Python path:", sys.path)
print("Python executable:", sys.executable)

try:
    from twilio.rest import Client
    print("Successfully imported twilio")
except ImportError as e:
    print("Error importing twilio:", str(e))
    print("Full error:", e.__class__.__name__)

from flask import current_app

def send_sms(to_number, message):
    try:
        # Get Twilio credentials from config
        account_sid = current_app.config['TWILIO_ACCOUNT_SID']
        auth_token = current_app.config['TWILIO_AUTH_TOKEN']
        from_number = current_app.config['TWILIO_PHONE_NUMBER']

        # Initialize Twilio client
        client = Client(account_sid, auth_token)

        # Send message
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        
        print(f"SMS sent successfully! SID: {message.sid}")
        return True
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return False

def send_rsvp_notification(phone_number, message):
    """Send RSVP notification to event creator"""
    if not phone_number:
        print("No phone number available for RSVP notification")
        return False
    
    try:
        return send_sms(phone_number, message)
    except Exception as e:
        print(f"Failed to send RSVP notification: {str(e)}")
        return False

def send_event_reminder(event, user):
    if not user.phone_number:
        print(f"User {user.username} has no phone number set")
        return False

    message = f"⏰ Reminder: Your event '{event.title}' is starting soon at {event.event_datetime.strftime('%I:%M %p')}!"
    return send_sms(user.phone_number, message) 