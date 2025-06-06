# app/models.py
from enum import Enum

from flask import current_app
from sqlalchemy import CheckConstraint

from .extensions import db
from flask_security import UserMixin, RoleMixin  # Add RoleMixin
from datetime import datetime  # Often useful for confirmed_at, etc.
from enum import Enum as PyEnum
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from .sms import send_sms as send_sms_notification

# Association table for bi-directional friendships
friendships = db.Table('friendships',
                       db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                       db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
                       )

# >>> START Flask-Security additions <<<
# Association table for Users and Roles
roles_users = db.Table('roles_users', db.Model.metadata,
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id', ondelete="CASCADE"), primary_key=True), # Add primary_key=True
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id', ondelete="CASCADE"), primary_key=True)  # Add primary_key=True
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
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)

    # Self-referencing many-to-many for friendships
    friends = db.relationship(
        'User',
        secondary=friendships,
        primaryjoin=(friendships.c.user_id == id),
        secondaryjoin=(friendships.c.friend_id == id),
        backref=db.backref('friend_of', lazy='dynamic'),
        lazy='dynamic'
    )

    # >>> START Flask-Security additions <<<
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    # >>> END Flask-Security additions <<<

    def friend_ids(self):
        return [friend.id for friend in self.friends]

    def add_friend(self, user_to_add):
        if not self.is_friend(user_to_add):
            self.friends.append(user_to_add)
            user_to_add.friends.append(self)  # mutual friendship
            
            # Send notification to the user being added
            from .sms import send_notification
            notification_message = f"{self.username} added you to their flock!"
            notification_link = f"/profile/{self.username}"
            send_notification(
                user_id=user_to_add.id,
                message=notification_message,
                notification_type='friend_request',
                link=notification_link
            )
            return True
        return False  # already friends or trying to add myself as friend

    def remove_friend(self, user_to_remove):
        if self.is_friend(user_to_remove):
            self.friends.remove(user_to_remove)
            user_to_remove.friends.remove(self)  # mutual friendship
            return True
        return False  # Not friends

    def is_friend(self, user_to_check):
        if user_to_check == self:  # can't be friends with my own self
            return False
        return user_to_check in self.friends

    def friend_count(self):
        if self.friends:
            return self.friends.count()
        return 0

    def __repr__(self):
        return f"<User {self.username}>"

    def get_friend_recommendations(self, limit=15): 
        from sqlalchemy import func
        
        # Get IDs of current friends
        friend_ids = self.friend_ids()
        
        # Get friends of friends who aren't already friends
        friends_of_friends = User.query\
            .join(friendships, User.id == friendships.c.friend_id)\
            .filter(friendships.c.user_id.in_(friend_ids))\
            .filter(User.id != self.id)\
            .filter(~User.id.in_(friend_ids))\
            .group_by(User.id)\
            .order_by(func.count(User.id).desc())\
            .limit(limit)\
            .all()
            
        return friends_of_friends

    def get_popular_posts(self, limit=15):
        from sqlalchemy import func
        
        # Get IDs of friends and friends of friends in a single query
        friend_ids = self.friend_ids()
        
        # Get friends of friends IDs
        friend_of_friend_ids = db.session.query(friendships.c.friend_id)\
            .filter(friendships.c.user_id.in_(friend_ids))\
            .filter(friendships.c.friend_id != self.id)\
            .filter(~friendships.c.friend_id.in_(friend_ids))\
            .distinct()\
            .all()
            
        friend_of_friend_ids = [f[0] for f in friend_of_friend_ids]
        all_relevant_ids = friend_ids + friend_of_friend_ids
        
        # Get posts from friends and friends of friends
        posts = Post.query\
            .filter(Post.user_id.in_(all_relevant_ids))\
            .filter(Post.visibility == VisibilityEnum.PUBLIC)\
            .all()
            
        # Sort by popularity score
        sorted_posts = sorted(posts, key=lambda x: x.popularity_score(), reverse=True)
        return sorted_posts[:limit]


class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.Enum(VisibilityEnum), default=VisibilityEnum.PUBLIC, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    likes = db.relationship('Like', foreign_keys='Like.post_id', backref='liked_post_object', lazy='dynamic',
                            cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='commented_on_post', lazy='dynamic',
                               cascade="all, delete-orphan")
    media = db.Column(db.String(255), nullable=True)

    def popularity_score(self):
        from datetime import datetime, timedelta
        
        # Base score from likes and comments
        like_weight = 1.0
        comment_weight = 2.0  # Comments are weighted more than likes
        
        base_score = (self.like_count() * like_weight) + (self.comment_count() * comment_weight)
        
        # Time decay factor (posts get less popular over time)
        hours_old = (datetime.utcnow() - self.timestamp).total_seconds() / 3600
        decay_factor = 1.0 / (1.0 + (hours_old / 24))  # 24-hour half-life
        
        return base_score * decay_factor

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return Like.query.filter_by(user_id=user.id, post_id=self.id).first() is not None

    def comment_count(self):
        return self.comments.count()


class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete="CASCADE"), nullable=True)
    share_id = db.Column(db.Integer, db.ForeignKey('share.id', ondelete="CASCADE"), nullable=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    likes = db.relationship('Like', foreign_keys='Like.comment_id', backref='liked_comment_object', lazy='dynamic',
                            cascade="all, delete-orphan")

    __table_args__ = (
        # Only ONE of post_id or share_id must be non-null at once
        CheckConstraint(
            "(CASE WHEN post_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN share_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_comment_target_exclusive"
        ),
    )

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
    comments = db.relationship('Comment', foreign_keys='Comment.share_id', backref='commented_on_share', lazy='dynamic',
                               cascade="all, delete-orphan")

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return Like.query.filter_by(user_id=user.id, share_id=self.id).first() is not None

    def comment_count(self):
        return self.comments.count()


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


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=db.backref('received_messages', lazy='dynamic'))

    def __repr__(self):
        return f"<Message {self.id}: {self.sender_id} -> {self.recipient_id}>"


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False, default='default')
    link = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))

    def to_dict(self):
        try:
            return {
                'id': self.id,
                'message': self.message,
                'type': self.notification_type,
                'link': self.link,
                'timestamp': self.timestamp.isoformat() + 'Z' if self.timestamp else None,  # Add 'Z' to indicate UTC
                'is_read': bool(self.is_read)  # Ensure boolean type
            }
        except Exception as e:
            current_app.logger.error(f"Error converting notification {self.id} to dict: {str(e)}")
            # Return a safe fallback
            return {
                'id': self.id,
                'message': str(self.message) if self.message else 'Error loading message',
                'type': str(self.notification_type) if self.notification_type else 'default',
                'link': str(self.link) if self.link else None,
                'timestamp': None,
                'is_read': False
            }

class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    event_datetime = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    max_participants = db.Column(db.Integer, nullable=True)
    
    # Relationships
    creator = db.relationship('User', backref=db.backref('created_events', lazy='dynamic'), 
                            foreign_keys=[creator_id])
    collaborators = db.relationship('User', 
                                  secondary='event_collaborators',
                                  backref=db.backref('collaborated_events', lazy='dynamic'),
                                  lazy='dynamic')
    rsvps = db.relationship('EventRSVP', backref='event', lazy='dynamic', cascade="all, delete-orphan")

    def add_collaborator(self, user):
        if user not in self.collaborators:
            self.collaborators.append(user)
            # Send notification
            from .sms import send_notification
            send_notification(
                user_id=user.id,
                message=f"You've been added as a collaborator to event: {self.title}",
                notification_type='event_collaboration',
                link=f"/events/{self.id}"
            )
            return True
        return False

    def remove_collaborator(self, user):
        if user in self.collaborators:
            self.collaborators.remove(user)
            return True
        return False

    def add_rsvp(self, user):
        from .sms import send_rsvp_notification
        if user in self.rsvps:
            return False, "You have already RSVP'd to this event."
        
        if self.max_participants and self.rsvps.count() >= self.max_participants:
            return False, "Sorry, this event is full."
        
        rsvp = EventRSVP(user=user, event=self)
        db.session.add(rsvp)
        db.session.commit()
        
        # Send SMS notification
        message = f"🎉 {user.username} has RSVP'd to your event '{self.title}'!"
        send_rsvp_notification(self.creator.phone, message)
        
        return True, "Successfully RSVP'd to the event."

    def remove_rsvp(self, user):
        rsvp = EventRSVP.query.filter_by(event_id=self.id, user_id=user.id).first()
        if rsvp:
            db.session.delete(rsvp)
            return True
        return False

    def can_edit(self, user):
        return (user.id == self.creator_id or 
                user in self.collaborators)

class EventCollaborator(db.Model):
    __tablename__ = 'event_collaborators'
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete="CASCADE"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

class EventRSVP(db.Model):
    __tablename__ = 'event_rsvp'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    user = db.relationship('User', backref=db.backref('event_rsvps', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='unique_event_rsvp'),
    )
