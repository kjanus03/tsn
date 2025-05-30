# tsn_app/graph_models.py
from neomodel import (StructuredNode, StringProperty, IntegerProperty, UniqueIdProperty, RelationshipTo,
                      RelationshipFrom)


class UserNode(StructuredNode):
    uid = UniqueIdProperty()  # internal graph ID
    user_id = IntegerProperty(unique_index=True)  # FK to your SQL User.id
    username = StringProperty(unique_index=True)

    # FRIEND relationship between users
    friends = RelationshipTo('UserNode', 'FRIENDS_WITH')

    # INTERESTS relationship to InterestNode
    interests = RelationshipTo('InterestNode', 'INTERESTED_IN')

    # LIKES relationship to PostNode
    likes = RelationshipTo('PostNode', 'LIKES')


class InterestNode(StructuredNode):
    name = StringProperty(unique_index=True)
    users = RelationshipFrom('UserNode', 'INTERESTED_IN')


class PostNode(StructuredNode):
    post_id = IntegerProperty(unique_index=True)  # FK to your SQL Post.id
    content = StringProperty()
    author = RelationshipFrom('UserNode', 'AUTHORED')
    liked_by = RelationshipFrom('UserNode', 'LIKES')

