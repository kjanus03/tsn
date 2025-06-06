from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore
from app.extensions import db, security
from app.models import User, Role
from app.config import Config
import uuid

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
security.init_app(app, SQLAlchemyUserDatastore(db, User, Role))

with app.app_context():
    password = input("Enter the password to hash: ")
    from flask_security.utils import hash_password
    hashed_password = hash_password(password)
    fs_uniquifier = str(uuid.uuid4())
    
    print("\nHashed password:")
    print(hashed_password)
    print("\nfs_uniquifier (UUID):")
    print(fs_uniquifier) 