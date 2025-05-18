# app/main/routes.py
from flask import Blueprint, render_template, request, redirect, url_for
# from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin
from flask_login import LoginManager, login_user, logout_user, current_user, login_required

from ..models import Post, VisibilityEnum
from .. import db

bp = Blueprint('main', __name__, template_folder='templates')

@bp.route('/')
def index():
    return render_template('main/index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    # get posts
    posts = Post.query.filter(
        (Post.visibility == VisibilityEnum.PUBLIC) |
        ((Post.visibility == VisibilityEnum.FRIENDS) & (Post.user_id.in_(current_user.friend_ids()))) |
        ((Post.visibility == VisibilityEnum.PRIVATE) & (Post.user_id == current_user.id))
    ).all()

    return render_template('main/dashboard.html', posts=posts)

@bp.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        content = request.form['content']
        visibility = request.form['visibility']
        post = Post(
            user_id=current_user.id,
            content=content,
            visibility=VisibilityEnum(visibility)
        )
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('main.dashboard'))

    return render_template('main/create_post.html')