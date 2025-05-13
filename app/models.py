# app/models.py
from enum import Enum
from . import db
from flask_user import UserMixin

# Association table for bi-directional friendships
friendships = db.Table('friendships', db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True))


class VisibilityEnum(Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')
    username = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=True, unique=True)
    email_confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable=False)
    liked_posts = db.relationship('Like', backref='user', lazy='dynamic')


    # Self-referencing many-to-many for friendships
    friends = db.relationship('User', secondary=friendships, primaryjoin=(friendships.c.user_id == id),
        secondaryjoin=(friendships.c.friend_id == id),
                              backref='friend_of')

    def friend_ids(self):
        """Return a list of user IDs that this user considers friends."""
        return [friend.id for friend in self.friends]

    def __repr__(self):
        return f"<User {self.username}>"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.Enum(VisibilityEnum), default=VisibilityEnum.PUBLIC, nullable=False)
    user = db.relationship('User', backref='posts')
    likes = db.relationship('Like', backref='post', lazy='dynamic')

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        return self.likes.filter_by(user_id=user.id).first() is not None

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_like'),)
