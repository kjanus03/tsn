from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
from app import db
from app.models import User
from app.profile.forms import EditProfileForm  # Create a WTForm for profile editing

bp = Blueprint('profile', __name__, template_folder='templates')

@bp.route('/profile/<username>')
@login_required
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile/view.html', user=user)

@bp.route('/profile/edit', methods=['GET', 'POST'])
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
