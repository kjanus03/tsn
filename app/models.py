# app/models.py
from enum import Enum
from . import db
from flask_security import UserMixin, RoleMixin # Add RoleMixin
from datetime import datetime # Often useful for confirmed_at, etc.

# Association table for bi-directional friendships
friendships = db.Table('friendships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# >>> START Flask-Security additions <<<
# Association table for Users and Roles
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    __tablename__ = 'role' # Explicit table name is good practice
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name
# >>> END Flask-Security additions <<<

class VisibilityEnum(Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class User(db.Model, UserMixin):
    __tablename__ = 'user' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    # 'active' is for Flask-Security.
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')
    username = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=True, unique=True)
    # Flask-Security uses 'confirmed_at' by default if SECURITY_CONFIRMABLE=True
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable=False)

    # Self-referencing many-to-many for friendships
    friends = db.relationship(
        'User',
        secondary=friendships,
        primaryjoin=(friendships.c.user_id == id),
        secondaryjoin=(friendships.c.friend_id == id),
        backref='friend_of'
    )

    # >>> START Flask-Security additions <<<
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    # >>> END Flask-Security additions <<<

    def friend_ids(self):
        """Return a list of user IDs that this user considers friends."""
        return [friend.id for friend in self.friends]

    def __repr__(self):
        return f"<User {self.username}>"

class Post(db.Model):
    __tablename__ = 'post' # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.Enum(VisibilityEnum), default=VisibilityEnum.PUBLIC, nullable=False)
    user = db.relationship('User', backref=db.backref('posts', lazy='dynamic')) # Added lazy='dynamic'