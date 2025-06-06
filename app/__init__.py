# tsn/app/__init__.py
import os
from flask import Flask, template_rendered, request
from flask_security import SQLAlchemyUserDatastore
from .extensions import db, migrate, socketio, security, csrf, mail, login_manager
from .config import Config

# ---> IMPORT YOUR CUSTOM FORM CLASS DIRECTLY <---
from .auth.forms import ExtendedRegisterForm # Path: app/security/forms.py
from flask_dance.contrib.google import make_google_blueprint

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def create_app(config_class=Config):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')

    app = Flask(__name__,
                template_folder=template_dir,
                static_folder=static_dir)
    app.config.from_object(config_class) # Loads SECURITY_REGISTER_TEMPLATE, etc.

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    
    # Configure mail with debug
    mail.init_app(app)
    if app.debug:
        import logging
        logging.basicConfig()
        logging.getLogger('flask_mail').setLevel(logging.DEBUG)

    # --- SIGNAL HANDLER ---
    @template_rendered.connect_via(app)
    def _template_rendered_debug(sender, template, context, **extra):
        # Only log for the /register route to avoid too much noise
        if request and request.path == sender.config.get('SECURITY_REGISTER_URL', '/register'):
            print(f"--- TEMPLATE RENDERED for {request.path} ---")
            print(f"Template filename: {template.name}")  # template.name is the path used in render_template
            print(f"Template object: {template}")
            if 'register_user_form' in context:
                print(f"Form object in context: {context['register_user_form'].__class__.__name__}")
            else:
                print(f"Form object 'register_user_form' NOT in context.")
            print(f"--- END TEMPLATE RENDERED ---")

    # --- END SIGNAL HANDLER ---

    # --- THIS IS THE MOST IMPORTANT PART FOR CUSTOM FORM ---
    # Explicitly set the FORM CLASS OBJECT in app.config
    app.config['SECURITY_REGISTER_FORM'] = ExtendedRegisterForm # Assign the imported class
    
    # Explicitly set the password reset templates
    app.config['SECURITY_FORGOT_PASSWORD_TEMPLATE'] = 'security/forgot_password.html'
    app.config['SECURITY_RESET_PASSWORD_TEMPLATE'] = 'security/reset_password.html'
    app.config['SECURITY_RECOVERABLE'] = True
    # -------------------------------------------------------

    # Add a debug print IMMEDIATELY AFTER loading config
    print(
        f"DEBUG: Value of SECURITY_REGISTER_TEMPLATE from app.config AFTER from_object: {app.config.get('SECURITY_REGISTER_TEMPLATE')}")
    print(
        f"DEBUG: Value of SECURITY_FORGOT_PASSWORD_TEMPLATE from app.config: {app.config.get('SECURITY_FORGOT_PASSWORD_TEMPLATE')}")
    print(
        f"DEBUG: Value of SECURITY_RESET_PASSWORD_TEMPLATE from app.config: {app.config.get('SECURITY_RESET_PASSWORD_TEMPLATE')}")
    print(
        f"DEBUG: Value of SECURITY_RECOVERABLE from app.config: {app.config.get('SECURITY_RECOVERABLE')}")

    with app.app_context():
        from .models import User, Role

    user_datastore = SQLAlchemyUserDatastore(db, User, Role)

    # Initialize Flask-Security. It will now read SECURITY_REGISTER_FORM from app.config
    # and should see your ExtendedRegisterForm class object.
    security.init_app(app, user_datastore)

    # Create admin role if it doesn't exist
    with app.app_context():
        admin_role = user_datastore.find_or_create_role('admin', description='Administrator')
        db.session.commit()

    # --- REVISED DEBUG PRINTS ---
    print(f"--- AFTER SECURITY INIT - REVISED DIVE ---")
    print(f"1. app.config['SECURITY_REGISTER_TEMPLATE']: {app.config.get('SECURITY_REGISTER_TEMPLATE')}")
    print(
        f"2. app.config['SECURITY_REGISTER_FORM'] (class object from app.config): {app.config.get('SECURITY_REGISTER_FORM')}")

    # ---- Flask-Dance Google Blueprint Setup ----
    google_bp = make_google_blueprint(
        client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
        # Scopes define what information you're asking Google for
        scope=[
            "openid",  # Standard for OpenID Connect
            "https://www.googleapis.com/auth/userinfo.email",  # For email
            "https://www.googleapis.com/auth/userinfo.profile",  # For name, profile pic
            "https://www.googleapis.com/auth/user.birthday.read",  # For birthday
            "https://www.googleapis.com/auth/user.gender.read",  # For gender (check current availability)
            "https://www.googleapis.com/auth/user.phonenumbers.read" # For phone (requires People API enabled & verification)
        ],
        # This is where Google redirects AFTER successful auth.
        # redirect_to="auth.handle_google_auth", # 'auth' is your blueprint, 'handle_google_auth' is your route
    )
    app.register_blueprint(google_bp, url_prefix="/login")  # Makes routes like /login/google

    # Try to access the form mapping directly if it exists
    # The 'forms' attribute might be a dictionary or a FormRegistry like object
    actual_register_form_class = None
    if hasattr(security, 'forms'):  # 'forms' is a common attribute name for the registry
        if isinstance(security.forms, dict) and 'register_form' in security.forms:
            form_wrapper = security.forms['register_form']
            actual_register_form_class = getattr(form_wrapper, 'cls', form_wrapper)  # .cls for newer, direct for older
        elif hasattr(security.forms, 'get_form_class'):  # Method in some versions
            actual_register_form_class = security.forms.get_form_class('register')  # or 'register_form'
        elif hasattr(security.forms, 'register_form'):  # Direct attribute sometimes
            actual_register_form_class = security.forms.register_form

    print(f"3. Security object's actual resolved REGISTER form CLASS: {actual_register_form_class}")

    print(f"--- END AFTER SECURITY INIT - REVISED DIVE ---")

    # Register blueprints
    from .main.routes import bp as main_bp
    app.register_blueprint(main_bp)

    from .profile.routes import bp as profile_bp
    app.register_blueprint(profile_bp)

    from .connections.routes import bp as connections_bp
    app.register_blueprint(connections_bp)

    from .admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    from .event.routes import events_bp as events_bp
    app.register_blueprint(events_bp)

    from .sockets import init_socketio_events
    init_socketio_events(socketio)

    return app