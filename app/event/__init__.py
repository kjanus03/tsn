from flask import Blueprint

events_bp = Blueprint('event', __name__)

from . import routes
