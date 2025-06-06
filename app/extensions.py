# tsn/app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_security import Security
from flask_wtf import CSRFProtect
from flask_login import LoginManager
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()
security = Security()
csrf = CSRFProtect()
login_manager = LoginManager()
mail = Mail()