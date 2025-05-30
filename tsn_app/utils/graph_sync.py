# tsn_app/utils/graph_sync.py
import logging

from neomodel import db, config
from tsn_app.graph_models import UserNode, PostNode


def init_neo4j(app):
    config.DATABASE_URL = (
        f"bolt://{app.config['NEO4J_USERNAME']}:{app.config['NEO4J_PASSWORD']}@{app.config['NEO4J_HOST']}:7687"
    )
    config.ENCRYPTED = True
    config.MAX_POOL_SIZE = 50
    print(f"Connecting to Neo4j at {config.DATABASE_URL}")


def sync_user(sql_user):
    # Create or update UserNode
    node = UserNode.nodes.get_or_none(user_id=sql_user.id)
    if not node:
        node = UserNode(user_id=sql_user.id, username=sql_user.username).save()
    else:
        node.username = sql_user.username
        node.save()
    return node


def sync_post(sql_post):
    node = PostNode.nodes.get_or_none(post_id=sql_post.id)
    if not node:
        node = PostNode(post_id=sql_post.id, content=sql_post.content).save()
    else:
        node.content = sql_post.content
        node.save()
    # Link author
    author_node = sync_user(sql_post.author)
    author_node.AUTHORED.connect(node)
    return node
