import os


# app/config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key')
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/tsn_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Security settings
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'a_very_secure_salt_CHANGE_ME'
    SECURITY_REMEMBER_SALT = os.environ.get('SECURITY_REMEMBER_SALT', 'a-test-salt-remember')
    SECURITY_REGISTERABLE = True
    SECURITY_REGISTER_TEMPLATE = 'security/register_user.html' # This is correct
    SECURITY_LOGIN_TEMPLATE = 'security/login_user.html'
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_CONFIRMABLE = False
    SECURITY_CHANGEABLE = True
    SECURITY_LOGIN_WITHOUT_CONFIRMATION = True
    SECURITY_POST_LOGIN_VIEW = 'main.dashboard'
    SECURITY_POST_LOGOUT_VIEW = 'main.index'
    SECURITY_POST_REGISTER_VIEW = 'main.dashboard' # Or 'security.login' to force login after register
    SECURITY_RECOVERABLE = True
    SECURITY_FORGOT_PASSWORD_TEMPLATE = 'security/forgot_password.html'
    SECURITY_RESET_PASSWORD_TEMPLATE = 'security/reset_password.html'
    SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = 'Nest - Password Reset Instructions'
    SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE = 'Nest - Your password has been reset'
    SECURITY_EMAIL_SUBJECT_PASSWORD_CHANGE_NOTICE = 'Nest - Your password has been changed'
    SECURITY_EMAIL_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or str(os.environ.get('MAIL_USERNAME'))
    SECURITY_EMAIL_PLAINTEXT = True  
    SECURITY_EMAIL_HTML = True
    SECURITY_RESET_PASSWORD_TEMPLATE_PLAINTEXT = 'security/email/reset_password.txt'

    # Google Services
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")


    # Mail settings for Outlook/Office 365
    MAIL_SERVER = 'smtp.office365.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')