from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from flask_security import roles_required
from sqlalchemy import func, distinct, extract
from datetime import datetime, timedelta
from ..models import User, Post, Comment, Like, Message, GenderEnum, Share
from ..extensions import db
from . import admin_bp
from flask_wtf import FlaskForm

class AdminForm(FlaskForm):
    pass  # Empty form just for CSRF protection

@admin_bp.route('/dashboard')
@login_required
@roles_required('admin')
def dashboard():
    # Get basic statistics
    total_users = User.query.count()
    total_posts = Post.query.count()
    total_comments = Comment.query.count()
    total_likes = Like.query.count()
    
    # Get stats for the last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    new_users = User.query.filter(User.date_joined >= seven_days_ago).count()
    new_posts = Post.query.filter(Post.timestamp >= seven_days_ago).count()
    new_comments = Comment.query.filter(Comment.timestamp >= seven_days_ago).count()
    new_likes = Like.query.filter(Like.timestamp >= seven_days_ago).count()
    
    # Get most active users (by post count)
    active_users = User.query.join(Post).group_by(User.id).order_by(func.count(Post.id).desc()).limit(5).all()
    
    # Get recent activity
    recent_posts = Post.query.order_by(Post.timestamp.desc()).limit(5).all()
    form = AdminForm()  # Create form instance for CSRF protection

    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_posts=total_posts,
                         total_comments=total_comments,
                         total_likes=total_likes,
                         new_users=new_users,
                         new_posts=new_posts,
                         new_comments=new_comments,
                         new_likes=new_likes,
                         active_users=active_users,
                         recent_posts=recent_posts,
                         form=form)

@admin_bp.route('/users')
@login_required
@roles_required('admin')
def user_management():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/statistics')
@login_required
@roles_required('admin')
def statistics():
    # Get total counts first
    total_users = db.session.query(func.count(User.id)).scalar() or 1  # Avoid division by zero
    total_posts = db.session.query(func.count(Post.id)).scalar() or 1
    total_likes = db.session.query(func.count(Like.id)).scalar() or 0
    total_shares = db.session.query(func.count(Share.id)).scalar() or 0
    total_comments = db.session.query(func.count(Comment.id)).scalar() or 0

    # Calculate averages
    avg_posts_per_user = total_posts / total_users
    avg_likes_per_post = total_likes / total_posts
    avg_shares_per_post = total_shares / total_posts
    avg_comments_per_post = total_comments / total_posts

    # Get daily post activity for the last 30 days
    daily_posts = db.session.query(
        func.date(Post.timestamp).label('date'),
        func.count(Post.id).label('count')
    ).filter(
        Post.timestamp >= datetime.utcnow() - timedelta(days=30)
    ).group_by(
        func.date(Post.timestamp)
    ).order_by(
        func.date(Post.timestamp)
    ).all()

    # Get gender distribution
    gender_stats = db.session.query(
        func.cast(User.gender, db.String).label('gender'),
        func.count(User.id).label('count')
    ).group_by(
        User.gender
    ).all()

    # Get registration trend by month
    registration_trend = db.session.query(
        func.date_trunc('month', User.date_joined).label('date'),
        func.count(User.id).label('count')
    ).group_by(
        func.date_trunc('month', User.date_joined)
    ).order_by(
        func.date_trunc('month', User.date_joined)
    ).all()

    # Convert registration trend to list of dictionaries
    registration_trend = [
        {
            'date': row.date.strftime('%Y-%m-%d'),
            'count': row.count
        }
        for row in registration_trend
    ]

    # Get most active hours
    active_hours = db.session.query(
        extract('hour', Post.timestamp).label('hour'),
        func.count(Post.id).label('count')
    ).group_by(
        extract('hour', Post.timestamp)
    ).order_by(
        extract('hour', Post.timestamp)
    ).all()

    return render_template('admin/statistics.html',
                         avg_posts_per_user=avg_posts_per_user,
                         avg_likes_per_post=avg_likes_per_post,
                         avg_shares_per_post=avg_shares_per_post,
                         avg_comments_per_post=avg_comments_per_post,
                         daily_posts=daily_posts,
                         gender_stats=gender_stats,
                         registration_trend=registration_trend,
                         active_hours=active_hours)

@admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
@roles_required('admin')
def deactivate_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('You cannot deactivate your own account.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        user.active = False
        db.session.commit()
        flash(f'User {user.username} has been deactivated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deactivating the user.', 'danger')
        current_app.logger.error(f'Error deactivating user: {str(e)}')
    
    return redirect(url_for('admin.user_management')) 

@admin_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@login_required
@roles_required('admin')
def activate_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            return redirect(url_for('admin.dashboard'))
        
        user.active = True
        db.session.commit()
        flash(f'User {user.username} has been activated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while activating the user.', 'danger')
        current_app.logger.error(f'Error activating user: {str(e)}')
    
    return redirect(url_for('admin.user_management')) 