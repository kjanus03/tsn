# tsn_app/models.py
from enum import Enum

from sqlalchemy import CheckConstraint

from .extensions import db
from flask_security import UserMixin, RoleMixin  # Add RoleMixin
from datetime import datetime  # Often useful for confirmed_at, etc.
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
    __tablename__ = 'role'  # Explicit table name is good practice
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
    profile_pic = db.Column(db.String(255), nullable=False, default='images/default.jpg')
    posts = db.relationship('Post', backref='author', lazy='dynamic', foreign_keys='Post.user_id')
    biography = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    date_joined = db.Column(db.Date, nullable=False, default=datetime.utcnow())
    posts = db.relationship('Post', backref='author', lazy='dynamic', foreign_keys='Post.user_id',
                            cascade="all, delete-orphan")
    likes_given = db.relationship('Like', backref='user', lazy='dynamic', foreign_keys='Like.user_id',
                                  cascade="all, delete-orphan")
    # User.comments should be 'comments_authored' to distinguish from Post.comments
    comments_authored = db.relationship('Comment', backref='author', foreign_keys='Comment.user_id', lazy='dynamic',
                                        cascade="all, delete-orphan")
    shares_authored = db.relationship('Share', backref='author', foreign_keys='Share.user_id', lazy='dynamic',
                                      cascade="all, delete-orphan")

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
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.Enum(VisibilityEnum), default=VisibilityEnum.PUBLIC, nullable=False)
    # user = db.relationship('User', backref='posts')
    # likes = db.relationship('Like', backref='post', lazy='dynamic')
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    likes = db.relationship('Like', foreign_keys='Like.post_id', backref='liked_post_object', lazy='dynamic',
                            cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='commented_on_post', lazy='dynamic',
                               cascade="all, delete-orphan")  # Changed backref

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        # Check if there's a Like record linking this user to this specific post_id
        return Like.query.filter_by(user_id=user.id, post_id=self.id).first() is not None


class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    likes = db.relationship('Like', foreign_keys='Like.comment_id', backref='liked_comment_object', lazy='dynamic',
                            cascade="all, delete-orphan")

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return Like.query.filter_by(user_id=user.id, comment_id=self.id).first() is not None


class Share(db.Model):
    __tablename__ = 'share'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    original_post = db.relationship('Post', backref=db.backref('shares_of_this_post', lazy='dynamic'))

    likes = db.relationship('Like', foreign_keys='Like.share_id', backref='liked_share_object', lazy='dynamic',
                            cascade="all, delete-orphan")

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return Like.query.filter_by(user_id=user.id, share_id=self.id).first() is not None


class Like(db.Model):
    __tablename__ = 'like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)

    # fk to the liked items - only one set per Like
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete="CASCADE"), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete="CASCADE"), nullable=True)
    share_id = db.Column(db.Integer, db.ForeignKey('share.id', ondelete="CASCADE"), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=True)


    __table_args__ = (
        # a user can only like a specific post once
        db.UniqueConstraint('user_id', 'post_id', name='uq_user_post_like'),
        # a user can only like a specific comment once
        db.UniqueConstraint('user_id', 'comment_id', name='uq_user_comment_like'),
        # a user can only like a specific share once
        db.UniqueConstraint('user_id', 'share_id', name='uq_user_share_like'),

        # only ONE of post_id, comment_id, share_id must be non-null at once
        # so a like pertains to one object at a time
        CheckConstraint(
            "(CASE WHEN post_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN comment_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN share_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_like_target_exclusive"
        ),
    )

    # property to get the actual liked object
    @property
    def liked_object(self):
        if self.post_id:
            return Post.query.get(self.post_id)
        elif self.comment_id:
            return Comment.query.get(self.comment_id)
        elif self.share_id:
            return Share.query.get(self.share_id)
        return None

    @property
    def target_type(self):
        if self.post_id: return 'post'
        if self.comment_id: return 'comment'
        if self.share_id: return 'share'
        return None
