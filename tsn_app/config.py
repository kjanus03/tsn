import os


# tsn_app/config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key')
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
    SECURITY_RECOVERABLE = False # Disable if mail not set up
    SECURITY_POST_LOGIN_VIEW = 'main.dashboard'
    SECURITY_POST_LOGOUT_VIEW = 'main.index'
    SECURITY_POST_REGISTER_VIEW = 'main.dashboard'
    # Or 'security.login' to force login after register

    # Google Services
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

    NEO4J_HOST = os.environ.get('NEO4J_HOST', '9218b27a.databases.neo4j.io')
    NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'UO4Qrvc-_7mG3-9wpaVrcNeyVP01VjnDiw0FxbT6Wlk')

    # Remove MAIL_SERVER settings if SECURITY_SEND_REGISTER_EMAIL = False
    # MAIL_SERVER = 'smtp.office365.com'
    # MAIL_PORT = 587
    # MAIL_USE_TLS = True
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # This is what Flask-Mail uses as the default sender if not overridden elsewhere
    # It can be just the email or a tuple (Display Name, Email Address)
    # MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or ("TSN Platform",
    #                                                                 str(os.environ.get('MAIL_USERNAME')))
    #
    # --- Flask-Security Email Settings ---
    # SECURITY_EMAIL_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or str(os.environ.get('MAIL_USERNAME'))
    # Ensure these are enabled if you want the features:
    # SECURITY_SEND_REGISTER_EMAIL = True  # Or False if you don't want registration emails for now
    # SECURITY_CONFIRMABLE = True  # Or False
    # SECURITY_RECOVERABLE = True  # Or False (for password reset)
    # ... (other SECURITY settings) ...