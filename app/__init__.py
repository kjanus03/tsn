import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_security import Security, SQLAlchemyUserDatastore
# Flask-Login components used by Flask-Security or directly
from .config import Config

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()


def create_app(config_class=Config):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, '..', 'templates')

    app = Flask(__name__, template_folder=template_dir)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)  # Make sure sockets.py uses this socketio instance

    # Import models AFTER db is initialized and available
    from .models import User, Role  # << IMPORTANT: Import Role as well

    # Setup Flask-Security
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security = Security(app, user_datastore)

    # Register Blueprints
    from .main.routes import bp as main_bp
    from .profile.routes import bp as profile_bp
    from .connections.routes import bp as connections_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(connections_bp)

    # Sockets initialization (if you have a sockets.py with init_socketio_events)
    from .sockets import init_socketio_events
    init_socketio_events(socketio)

    return app
