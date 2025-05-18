import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/tsn_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    USER_APP_NAME = "TSN Platform"
    USER_ENABLE_EMAIL = False  # set to True to use email confirmation
    USER_ENABLE_USERNAME = True
    USER_REQUIRE_RETYPE_PASSWORD = False  # USER_REQUIRE_EMAIL = True

    # Flask-Security settings
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'a_very_secure_salt_CHANGE_ME'
    # To enable registration
    SECURITY_REGISTERABLE = True
    # To send registration emails (requires mail setup)
    SECURITY_SEND_REGISTER_EMAIL = True
    # To enable email confirmation
    SECURITY_CONFIRMABLE = True
    # To enable password recovery
    SECURITY_RECOVERABLE = True
    # To allow users to change their password
    SECURITY_CHANGEABLE = True
    # Where to redirect after login/logout/registration
    SECURITY_POST_LOGIN_VIEW = '/main/dashboard'  # Adjust to your actual dashboard route
    SECURITY_POST_LOGOUT_VIEW = '/main/'  # Adjust to your actual home/index route
    SECURITY_POST_REGISTER_VIEW = '/main/dashboard'  # Adjust


    # Mail settings if using confirmable, recoverable, etc.
    MAIL_SERVER = 'smtp.example.com'
    # ... other mail settings ...
