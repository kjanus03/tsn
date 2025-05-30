# tsn/tsn_app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_security import Security

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()
security = Security() # This creates an INSTANCE of the Security class