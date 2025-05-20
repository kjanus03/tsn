# app/models.py
from enum import Enum
from .extensions import db
from flask_security import UserMixin, RoleMixin # Add RoleMixin
from datetime import datetime # Often useful for confirmed_at, etc.
from enum import Enum as PyEnum
from sqlalchemy.dialects.postgresql import ENUM as PgEnum


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

class GenderEnum(PyEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"

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
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')
    username = db.Column(db.String(64), nullable=False, unique=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(64), nullable=False, unique=True)
    date_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(PgEnum(GenderEnum, name='genderenum', create_type=True), nullable=False)
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
    confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable=False)
    liked_posts = db.relationship('Like', backref='user', lazy='dynamic')
    profile_pic = db.Column(db.String(255), nullable=False, default='images/default.jpg')
    posts = db.relationship('Post', backref='author', lazy='dynamic', foreign_keys='Post.user_id')
    biography = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    date_joined = db.Column(db.Date, nullable=False, default=datetime.utcnow())

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
    # user = db.relationship('User', backref='posts')
    likes = db.relationship('Like', backref='post', lazy='dynamic')
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        return self.likes.filter_by(user_id=user.id).first() is not None

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_like'),)


