# from flask import Blueprint, render_template, request, redirect, url_for, flash
# from flask_login import current_user, login_required
# from .. import db
# from ..models import User
# from ..profile.forms import EditProfileForm  # Create a WTForm for profile editing
#
# bp = Blueprint('profile', __name__, template_folder='templates')
#
# @bp.route('register')
# @login_required
# def register(username):
#     user = User.query.filter_by(username=username).first_or_404()
#     return render_template('security/register_user.html', user=user)
#
# @bp.route('login', methods=['GET', 'POST'])
# @login_required
# def edit_profile():
#     form = EditProfileForm(obj=current_user)
#     if form.validate_on_submit():
#         # Update user fields
#         current_user.username = form.username.data
#         # Optionally update additional fields: bio, interests, etc.
#         db.session.commit()
#         flash('Profile updated successfully!', 'success')
#         return redirect(url_for('profile.view_profile', username=current_user.username))
#     return render_template('profile/edit.html', form=form)

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required, login_user, logout_user
from .. import db
from ..models import User
from ..profile.forms import EditProfileForm  # Create a WTForm for profile editing
from ..auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from flask_login import login_user
from datetime import datetime, timedelta
import secrets
import string

bp = Blueprint('profile', __name__, template_folder='templates')

@bp.route('register')
@login_required
def register(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('security/register_user.html', user=user)

@bp.route('login', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(obj=current_user)
    if form.validate_on_submit():
        # Update user fields
        current_user.username = form.username.data
        # Optionally update additional fields: bio, interests, etc.
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.view_profile', username=current_user.username))
    return render_template('profile/edit.html', form=form)

def generate_reset_token():
    """Generate a random token for password reset"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = generate_reset_token()
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            # In a real application, you would send an email here
            # For now, we'll just flash a message with the reset link
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            flash(f'Password reset link: {reset_url}')
            return redirect(url_for('auth.login'))
        flash('Email address not found')
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.query.filter_by(reset_token=token).first()
    if not user or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired password reset link')
        return redirect(url_for('auth.reset_password_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash('Your password has been reset')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
