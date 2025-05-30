from sqlalchemy import event
from .graph_sync import sync_user, sync_post
from tsn_app.models import User, Post


# After a new user is created in SQL, upsert them in Neo4j:
@event.listens_for(User, 'after_insert')
def _after_insert_user(mapper, connection, target):
    sync_user(target)


@event.listens_for(User, 'after_update')
def _after_update_user(mapper, connection, target):
    sync_user(target)


# And for posts:
@event.listens_for(Post, 'after_insert')
def _after_insert_post(mapper, connection, target):
    sync_post(target)


@event.listens_for(Post, 'after_update')
def _after_update_post(mapper, connection, target):
    sync_post(target)
