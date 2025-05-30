from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user, login_required
from .. import db
from ..models import User, Post, VisibilityEnum, Like, Share
from .forms import EditProfileForm  # Create a WTForm for profile editing
import os


bp = Blueprint('profile', __name__, template_folder='templates')

def save_picture(form_picture):
    """Saves uploaded picture and returns the filename."""
    if not form_picture:
        return current_user.profile_pic  # Return current pic if no new one is uploaded

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(form_picture.filename)
    if f_ext.lower() not in ['.png', '.jpg', '.jpeg',
                             '.gif']:  # Redundant if FileAllowed used, but good server-side check
        flash('Invalid image file type.', 'danger')
        return current_user.profile_pic  # Or handle error differently

    picture_fn = random_hex + f_ext
    # Create path relative to the 'static' folder.
    # Files should be saved within tsn_app.static_folder + '/images/profile_pics/'
    # tsn_app.static_folder is an absolute path. We need to join it.
    picture_path = os.path.join(current_app.static_folder, 'images', 'profile_pics', picture_fn)

    # Ensure the profile_pics directory exists
    profile_pics_dir = os.path.join(current_app.static_folder, 'images', 'profile_pics')
    os.makedirs(profile_pics_dir, exist_ok=True)

    try:
        form_picture.save(picture_path)
        # Return the path relative to the static folder for storing in DB and using in url_for
        return os.path.join('images', 'profile_pics', picture_fn).replace("\\", "/")  # Ensure forward slashes for URL
    except Exception as e:
        current_app.logger.error(f"Error saving picture: {e}")
        flash('Error saving profile picture.', 'danger')
        return current_user.profile_pic


@bp.route('/profile/<username>')
@bp.route('/profile/<username>/<view_type>')
@login_required
def view_profile(username, view_type=None):
    user = User.query.filter_by(username=username).first_or_404()

    # Determine which tab/view is active
    if view_type not in ['posts', 'likes', 'shares']:
        view_type = 'posts'  # Default to posts view

    items_to_display = []
    pagination_obj = None  # For potential pagination within tabs later

    items_per_page = current_app.config.get('PROFILE_ITEMS_PER_PAGE', 10)  # Configurable
    page = request.args.get('page', 1, type=int)

    if view_type == 'posts':
        # Fetch posts authored by this user
        # Apply visibility rules if viewing someone else's profile
        posts_query = Post.query.filter_by(author=user)
        if user != current_user:  # If viewing another user's profile
            # Only show public posts, or friends' posts if they are friends
            # This logic needs to be robust based on your friendship model
            is_friend = current_user.is_authenticated and user in current_user.friends
            if is_friend:
                posts_query = posts_query.filter(
                    (Post.visibility == VisibilityEnum.PUBLIC) |
                    (Post.visibility == VisibilityEnum.FRIENDS)
                )
            else:
                posts_query = posts_query.filter(Post.visibility == VisibilityEnum.PUBLIC)

        posts_query = posts_query.order_by(Post.timestamp.desc())
        pagination_obj = posts_query.paginate(page=page, per_page=items_per_page, error_out=False)
        items_to_display = pagination_obj.items
        active_tab = 'posts'

    elif view_type == 'likes':
        # Fetch posts/items liked by this user
        # This requires knowing what the user liked (posts, comments, shares)
        # For simplicity, let's assume we only show liked POSTS for now.
        # You'd need a more complex query or separate tabs if you want to show liked comments/shares.

        # Get Like objects where user_id is the profile user's ID and post_id is not null
        likes_query = Like.query.filter_by(user_id=user.id) \
            .filter(Like.post_id != None) \
            .order_by(Like.timestamp.desc())

        pagination_obj = likes_query.paginate(page=page, per_page=items_per_page, error_out=False)
        # items_to_display will be Like objects. The template will need to access like.liked_post_object
        items_to_display = pagination_obj.items
        active_tab = 'likes'

    elif view_type == 'shares':
        # Fetch posts shared by this user
        shares_query = Share.query.filter_by(author=user).order_by(Share.timestamp.desc())
        pagination_obj = shares_query.paginate(page=page, per_page=items_per_page, error_out=False)
        # items_to_display will be Share objects. The template will need to access share.original_post
        items_to_display = pagination_obj.items
        active_tab = 'shares'

    return render_template('profile/view.html',
                           profile_user=user,
                           items=items_to_display,  # Posts, Likes, or Shares
                           active_tab=active_tab,  # To highlight the active tab
                           pagination=pagination_obj)  # For pagination controls within t

@bp.route('/profile/<username>/edit', methods=['GET', 'POST'])
@login_required
def edit_profile(username):
    form = EditProfileForm(obj=current_user)  # Pre-populate form with current user's data using obj=
    # WTForms will match form field names to current_user attributes

    if form.validate_on_submit():
        # Update basic fields
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        current_user.date_birth = form.date_birth.data
        current_user.gender = form.gender.data  # WTForms SelectField provides the enum value
        current_user.biography = form.biography.data
        current_user.location = form.location.data

        # Handle profile picture update
        if form.profile_pic_upload.data:  # If a new file was uploaded
            # Optional: Delete old picture if it's not the default
            # if current_user.profile_pic and current_user.profile_pic != 'images/default_profile.jpg':
            #     old_pic_path = os.path.join(current_app.static_folder, current_user.profile_pic)
            #     if os.path.exists(old_pic_path):
            #         try:
            #             os.remove(old_pic_path)
            #         except Exception as e:
            #             current_app.logger.error(f"Error deleting old picture: {e}")

            picture_file_path_for_db = save_picture(form.profile_pic_upload.data)
            current_user.profile_pic = picture_file_path_for_db

        try:
            db.session.commit()
            flash('Your profile has been updated!', 'success')
            return redirect(
                url_for('profile.view_profile', username=current_user.username))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile. Please try again.', 'danger')
            current_app.logger.error(f"Profile update error: {e}", exc_info=True)


    elif request.method == 'GET':
        # Pre-fill the form with existing data (already done by obj=current_user)
        # form.username.data = current_user.username (not needed if render_kw={'readonly':True} and obj used)
        # form.email.data = current_user.email (not needed if render_kw={'readonly':True} and obj used)
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone.data = current_user.phone
        form.date_birth.data = current_user.date_birth
        form.gender.data = current_user.gender.value if current_user.gender else None  # Set current enum value for SelectField
        # form.about_me.data = current_user.about_me
        pass  # Form is already pre-populated by obj=current_user if attribute names match

    return render_template('profile/edit.html', title='Edit Profile', form=form)