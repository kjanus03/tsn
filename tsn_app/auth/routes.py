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
