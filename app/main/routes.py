# app/main/routes.py
import secrets
import uuid
from datetime import datetime, date
import os
from urllib.parse import urlencode
from sqlalchemy import or_, literal, text
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.google import google  # The proxy for the current Google session
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort, jsonify
# from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_security.utils import hash_password  # Or other utils
from dateutil.parser import parse as parse_date
from werkzeug.utils import secure_filename
from ..events import send_notification
from .forms import PostForm, EditPostForm, CommentForm
from ..models import Post, VisibilityEnum, Like, User, GenderEnum, Comment, Share, Message, Notification, roles_users
from .. import db, security

bp = Blueprint('main', __name__,
               template_folder='templates',
               static_folder='static')

ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_VIDEO_EXTENSIONS)


@bp.route('/')
def index():
    return render_template('main/index.html')


@bp.route('/users')
@login_required
def users():
    page = request.args.get('page', 1, type=int)  # For pagination later
    search_query = request.args.get('q', '').strip()  # Get search query, default to empty string

    # Exclude current user and admin users, but include users without roles
    admin_ids = db.session.query(roles_users.c.user_id).filter(roles_users.c.role_id == 2).subquery()
    query = User.query.filter(
        User.id != current_user.id,
        ~User.id.in_(admin_ids)
    )

    if search_query:
        # Simple search: username, first name, last name, email (be careful with email privacy)
        # Use ilike for case-insensitive search
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),  # Ensure you have first_name in User model
                User.last_name.ilike(search_term)  # Ensure you have last_name in User model
            )
        )

    # Order users, e.g., by username or registration date
    users_list = query.order_by(User.username.asc()).paginate(page=page, per_page=12)  # Example: 12 users per page
    # Using paginate for pagination

    return render_template('main/users.html',
                           title="Discover Users",
                           users_list=users_list,  # Pass the pagination object
                           search_query=search_query)  # Pass search query back for pre-filling search bar


@oauth_authorized.connect
def logged_in_with_google(blueprint, token):
    if blueprint.name != "google":
        return

    if not token:
        flash("Failed to log in with Google.", "error")
        return redirect(url_for("security.login"))

    google_user_info = None
    people_api_data = None  # For data from People API if needed

    try:
        # Get basic user info
        resp_userinfo = blueprint.session.get("/oauth2/v2/userinfo")
        resp_userinfo.raise_for_status()
        google_user_info = resp_userinfo.json()
        email = google_user_info.get("email")

        # To get richer profile data like birthday, gender, phone, you often need the People API
        # The 'google_id' is 'me' in People API context for the authenticated user
        google_person_id = google_user_info.get("sub")  # 'sub' is standard OIDC subject identifier (Google ID)

        if google_person_id:
            # Request specific fields: birthdays, genders, phoneNumbers
            # Note: You might get multiple entries for some of these (e.g., multiple phone numbers)
            # You'll need to pick the primary one or handle appropriately.
            person_fields = "names,emailAddresses,birthdays,genders,phoneNumbers"  # Add other fields as needed
            resp_people = blueprint.session.get(
                f"https://people.googleapis.com/v1/people/{google_person_id}?personFields={person_fields}"
            )
            if resp_people.ok:  # Check if the request was successful
                people_api_data = resp_people.json()
            else:
                current_app.logger.warning(
                    f"Failed to get extended info from People API: {resp_people.status_code} - {resp_people.text}")

    except Exception as e:
        current_app.logger.error(f"Could not fetch user info from Google/People API: {e}", exc_info=True)
        flash("Could not fetch user info from Google. Please try again.", "error")
        return redirect(url_for("security.login"))

    if not email:  # Email should come from userinfo
        flash("Email not provided by Google. Cannot log in.", "error")
        return redirect(url_for("security.login"))

    user = User.query.filter_by(email=email).first()

    if user:
        login_user(user)
        flash(f"Welcome back, {user.username or user.email}!", "success")
        return redirect(url_for('main.dashboard'))
    else:
        # --- NEW USER: PREPARE DATA FOR REGISTRATION FORM / DIRECT CREATION ---
        first_name = google_user_info.get("given_name")
        last_name = google_user_info.get("family_name")

        # Username generation (same as before)
        email_prefix = email.split('@')[0]
        base_username = (first_name or email_prefix).lower().replace(" ", "_")
        base_username = "".join(c if c.isalnum() or c == '_' else '' for c in base_username)
        if not base_username: base_username = f"user_{str(uuid.uuid4())[:6]}"
        temp_username = base_username
        counter = 0
        while User.query.filter_by(username=temp_username).first():
            counter += 1
            temp_username = f"{base_username}_{counter}"
        generated_username = temp_username

        # Extract birthday
        user_dob = date(1900, 1, 1)  # Default placeholder
        if people_api_data and people_api_data.get("birthdays"):
            for bday in people_api_data["birthdays"]:
                if bday.get("date") and bday.get("date").get("year") and bday.get("date").get("month") and bday.get(
                        "date").get("day"):
                    try:
                        user_dob = date(bday["date"]["year"], bday["date"]["month"], bday["date"]["day"])
                        break  # Take the first valid one
                    except ValueError:
                        current_app.logger.warning(f"Invalid birthday format from Google: {bday['date']}")

        # Extract gender
        user_gender = GenderEnum.PREFER_NOT_TO_SAY  # Default
        if people_api_data and people_api_data.get("genders"):
            for g in people_api_data["genders"]:
                google_gender_value = g.get("value", "").lower()
                if google_gender_value == "male":
                    user_gender = GenderEnum.MALE
                    break
                elif google_gender_value == "female":
                    user_gender = GenderEnum.FEMALE
                    break
                elif google_gender_value == "other":  # Or map as needed
                    user_gender = GenderEnum.OTHER
                    break

        # Extract phone number (take the first canonical one if available)
        user_phone = None  # Keep as None if not found, relies on User.phone being nullable
        if people_api_data and people_api_data.get("phoneNumbers"):
            for pn in people_api_data["phoneNumbers"]:
                if pn.get("canonicalForm") or pn.get("value"):  # Prefer canonicalForm
                    user_phone = pn.get("canonicalForm") or pn.get("value")
                    # Check if phone number already exists if it needs to be unique
                    if User.query.filter_by(phone=user_phone).first():
                        current_app.logger.warning(
                            f"Phone number {user_phone} from Google already exists. Not setting for new user {email}.")
                        user_phone = None  # Don't use it if it's taken and must be unique
                    break

        # Ensure all non-nullable fields in your User model are covered here
        user_data = {
            'email': email,
            'username': generated_username,
            'password': secrets.token_urlsafe(24),
            'first_name': first_name or "User",
            'last_name': last_name or "",
            'active': True,
            'confirmed_at': datetime.utcnow(),
            'fs_uniquifier': str(uuid.uuid4()),
            'date_birth': user_dob,  # From Google or placeholder
            'gender': user_gender,  # From Google or placeholder
            'phone': user_phone,  # From Google (will be None if not found/taken & model is nullable)
            # If User.phone is NOT nullable, you MUST provide a placeholder here
            # if user_phone is None.
        }

        # If phone is NOT nullable and no phone was found:
        if not user_data.get('phone') and not User.phone.nullable:
            user_data['phone'] = f"OAUTH_NO_PHONE_{str(uuid.uuid4())[:8]}"  # Placeholder if phone is required

        try:
            new_user = security.datastore.create_user(**user_data)
            # ... (assign roles, commit, login_user, flash, redirect) ...
            security.datastore.commit()
            login_user(new_user)
            flash("Account created via Google!", "success")
            return redirect(url_for("main.dashboard"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user {email} after Google (People API): {e}", exc_info=True)
            flash("An error occurred creating your account. Please try manual registration.", "danger")
            return redirect(url_for("security.register"))


# Optional: Handle OAuth errors
@oauth_error.connect
def google_oauth_error(blueprint, error, error_description=None, error_uri=None):
    flash(f"OAuth error from {blueprint.name}: {error} description: {error_description}", "error")
    current_app.logger.error(f"OAuth error from {blueprint.name}: {error} desc: {error_description} uri: {error_uri}")
    return redirect(url_for("security.login"))

# You need to make sure these signal handlers are connected when the app is created.
# If this code is in app/__init__.py, it should be fine.
# If it's in a separate file (e.g., app/oauth_handlers.py), import that file in app/__init__.py
# so the @oauth_authorized.connect decorator runs.


def save_post_media(form_media_file):
    if not form_media_file or not form_media_file.filename:
        return None  # No file uploaded

    original_filename = secure_filename(form_media_file.filename)
    _, f_ext = os.path.splitext(original_filename)

    if f_ext.lower() not in ALLOWED_EXTENSIONS:
        flash(f'Invalid file type: {f_ext}. Allowed types are images (png, jpg, gif) or videos (mp4, mov, avi, etc.).',
              'danger')
        current_app.logger.warning(f"Attempt to upload invalid file type: {original_filename}")
        return None

    random_hex = secrets.token_hex(8)
    unique_filename = random_hex + f_ext

    # Saving to instance folder is recommended for user uploads
    upload_subdir_instance = 'post_media'  # e.g., instance/post_media/
    full_upload_folder_path = os.path.join(current_app.instance_path, upload_subdir_instance)

    # Path to store in DB (relative to the 'instance' uploads concept)
    # e.g., "post_media/uniquefilename.jpg"
    relative_db_path = os.path.join(upload_subdir_instance, unique_filename).replace("\\", "/")

    os.makedirs(full_upload_folder_path, exist_ok=True)
    file_save_path = os.path.join(full_upload_folder_path, unique_filename)

    try:
        form_media_file.save(file_save_path)
        current_app.logger.info(f"Successfully saved media: {unique_filename} to {file_save_path}")
        return relative_db_path  # Return only the path
    except Exception as e:
        current_app.logger.error(f"Error saving media file {unique_filename}: {e}", exc_info=True)
        flash('An error occurred while saving your media.', 'danger')
        return None


@bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    post_form = PostForm()
    form = CommentForm()

    if post_form.validate_on_submit():
        current_app.logger.info("--- Dashboard POST request, form validated ---")
        media_path_for_db = None

        uploaded_file = post_form.media_upload.data  # Access file via the form field
        current_app.logger.info(f"post_form.media_upload.data: {uploaded_file}")  # Check if it's a FileStorage

        if uploaded_file and uploaded_file.filename:  # Check FileStorage object
            current_app.logger.info(f"FileField data present: {uploaded_file.filename}")
            saved_path = save_post_media(uploaded_file)  # Your existing save function
            if saved_path:
                media_path_for_db = saved_path
                current_app.logger.info(f"Media path for DB: {media_path_for_db}")
            else:
                current_app.logger.warning("save_post_media returned None. Post will be created without media.")
                # No need to redirect here, let the post creation continue without media
                # or add a specific flash message if media upload was attempted but failed.
        else:
            current_app.logger.info("No file data provided in post_form.media_upload.data")

        actual_user_object = current_user._get_current_object()
        new_post = Post(
            content=post_form.content.data,
            visibility=VisibilityEnum(post_form.visibility.data),
            author=actual_user_object,
            media=media_path_for_db  # Will be None if no file or save failed
        )
        db.session.add(new_post)
        try:
            db.session.commit()
            current_app.logger.info(
                f"Post committed to DB. Media path: {media_path_for_db if media_path_for_db else 'N/A'}")
            flash('Your post has been published!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error committing post to DB: {e}", exc_info=True)
            flash('Error publishing post.', 'danger')

        return redirect(url_for('main.dashboard'))
    elif request.method == 'POST':  # Form submitted but validate_on_submit() was false
        flash('Please correct the errors below.', 'danger')
        current_app.logger.warning(f"Post form validation failed. Errors: {post_form.errors}")

    page = request.args.get('page', 1, type=int)
    actual_current_user = current_user._get_current_object()

    # Base conditions for posts visibility
    conditions = []
    conditions.append(Post.visibility == VisibilityEnum.PUBLIC)

    if actual_current_user.is_authenticated:
        friend_ids = actual_current_user.friend_ids()
        if friend_ids:
            conditions.append(
                (Post.visibility == VisibilityEnum.FRIENDS) & (Post.user_id.in_(friend_ids))
            )
        conditions.append(
            (Post.visibility == VisibilityEnum.PRIVATE) & (Post.user_id == actual_current_user.id)
        )

    # Get posts and shares as a union
    posts_query = Post.query.filter(or_(*conditions))
    shares_query = db.session.query(Share).join(Post).filter(or_(*conditions))

    # Combine posts and shares, ordered by timestamp
    combined_query = db.session.query(
        db.union(
            posts_query.with_entities(
                Post.id.label('id'),
                Post.timestamp.label('timestamp'),
                literal('post').label('type'),
                Post.id.label('original_id')
            ),
            shares_query.with_entities(
                Share.id.label('id'),
                Share.timestamp.label('timestamp'),
                literal('share').label('type'),
                Share.post_id.label('original_id')
            )
        ).alias()
    ).order_by(text('timestamp DESC'))

    # Paginate the combined results
    posts_per_page = current_app.config.get('POSTS_PER_PAGE', 10)
    page = request.args.get('page', 1, type=int)
    pagination = combined_query.paginate(page=page, per_page=posts_per_page, error_out=False)

    # Fetch the actual posts and shares
    items = []
    for item in pagination.items:
        if item.type == 'post':
            post = Post.query.get(item.id)
            if post:
                items.append(('post', post))
        else:
            share = Share.query.get(item.id)
            if share:
                items.append(('share', share))

    return render_template('main/dashboard.html',
                         post_form=post_form,
                         form=form,
                         items=items,
                         pagination=pagination)


@bp.route('/uploads/post_media/<path:filename>')  # URL pattern
# @login_required # Consider if media should always be public or require login/visibility checks
def uploaded_post_media(filename):  # Function name becomes part of the endpoint if not specified
    # This path MUST match where your save_post_media function saves the files.
    # If save_post_media saves to 'instance/post_media':
    media_directory = os.path.join(current_app.instance_path, 'post_media')

    current_app.logger.info(f"Attempting to serve: {filename} from {media_directory}")
    try:
        return send_from_directory(media_directory, filename, as_attachment=False)
    except FileNotFoundError:
        current_app.logger.error(f"File not found: {filename} in {media_directory}")
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error serving file {filename}: {e}", exc_info=True)
        abort(500)  # Or a more specific error

@bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user: # Or current_user._get_current_object() for strict comparison
        abort(403)  # Forbidden if not the author

    form = EditPostForm(obj=post) # Pre-populate form with existing post data

    if form.validate_on_submit():
        post.content = form.content.data
        post.visibility = VisibilityEnum(form.visibility.data) # Convert string back to Enum
        if form.new_media.data:
            # Delete old media if it exists and is being replaced
            new_media_path = save_post_media(form.new_media.data)
            if new_media_path:
                post.media = new_media_path
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('main.dashboard'))
    elif request.method == 'GET':
        form.content.data = post.content
        form.visibility.data = post.visibility.value

    return render_template('main/edit_post.html', title='Edit Post', form=form, post=post)


@bp.route('/post/<int:post_id>/delete', methods=['POST']) # Strictly POST for deletion
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)

    # deleting associated media from the filesystem
    if post.media:
        try:
            if post.media.startswith('post_media/'):
                media_filename = post.media.split('/')[-1] # Get just the filename
                media_path = os.path.join(current_app.instance_path, 'post_media', media_filename)
                if os.path.exists(media_path):
                    os.remove(media_path)
                    current_app.logger.info(f"Deleted media file: {media_path}")
        except Exception as e:
            current_app.logger.error(f"Error deleting media file for post {post.id}: {e}")

    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted.', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    try:
        if existing_like:
            db.session.delete(existing_like)
        else:
            like = Like(user_id=current_user.id, post_id=post.id)
            db.session.add(like)
            
            # Send notification to post author if it's not their own post
            if post.user_id != current_user.id:
                notification_message = f"{current_user.username} seeded your hatch"
                notification_link = f"/post/{post.id}"
                send_notification(
                    user_id=post.user_id,
                    message=notification_message,
                    notification_type='like',
                    link=notification_link
                )

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error liking/unliking post: {e}")
        flash('Error processing like.', 'danger')

    return redirect(request.referrer or url_for('main.dashboard'))

@bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    comment_text = request.form.get('comment_text')

    if not comment_text:
        flash('Comment cannot be empty.', 'danger')
        return redirect(request.referrer or url_for('main.dashboard'))

    new_comment = Comment(
        content=comment_text,
        user_id=current_user.id,
        post_id=post.id
    )
    db.session.add(new_comment)
    
    # Send notification to post author if it's not their own comment
    if post.user_id != current_user.id:
        notification_message = f"{current_user.username} peeped your hatch: {comment_text[:30]}"
        notification_link = f"/post/{post.id}"
        send_notification(
            user_id=post.user_id,
            message=notification_message,
            notification_type='comment',
            link=notification_link
        )
        
    try:
        db.session.commit()
        flash('Your comment has been added.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding comment: {e}")
        flash('Error adding comment.', 'danger')

    return redirect(request.referrer or url_for('main.dashboard') + f"#post-{post.id}")


@bp.route('/message')
def message():
    return render_template('main/message.html')

@bp.route('/messages')
@login_required
def messages():
    friends = current_user.friends.order_by(User.first_name).all() if hasattr(current_user.friends, 'order_by') else list(current_user.friends)
    return render_template('main/messages.html', friends=friends)

@bp.route('/messages/history/<int:friend_id>')
@login_required
def message_history(friend_id):
    friend = User.query.get_or_404(friend_id)
    if not current_user.is_friend(friend):
        return jsonify({'error': 'Not friends'}), 403

    messages = (
        db.session.query(Message)
        .filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == friend_id)) |
            ((Message.sender_id == friend_id) & (Message.recipient_id == current_user.id))
        )
        .order_by(Message.timestamp.asc())
        .all()
    )
    messages_data = [
        {
            'id': m.id,
            'sender_id': m.sender_id,
            'recipient_id': m.recipient_id,
            'content': m.content,
            'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        for m in messages
    ]
    return jsonify(messages_data)

@bp.route('/post/<int:post_id>/share', methods=['GET', 'POST'])
@login_required
def share_post(post_id):
    post = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        # Handle the share creation
        share_content = request.form.get('share_content')
        new_share = Share(
            user_id=current_user.id,
            post_id=post_id,
            content=share_content if share_content else None
        )
        db.session.add(new_share)
        try:
            # Send notification to post author if it's not their own share
            if post.user_id != current_user.id:
                notification_message = f"{current_user.username} echoed your hatch"
                notification_link = f"/post/{post.id}"
                send_notification(
                    user_id=post.user_id,
                    message=notification_message,
                    notification_type='share',
                    link=notification_link
                )
            
            db.session.commit()
            flash('Post shared successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error sharing post: {e}")
            flash('Error sharing post.', 'danger')
        return redirect(url_for('main.dashboard'))

    # For GET requests or XHR requests, return the existing share modal data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        post_url = url_for('main.view_post', post_id=post_id, _external=True)
        return jsonify({'post_url': post_url})

    return render_template('main/share_post.html', post=post)

@bp.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)

    # Check if the user has permission to view this post
    if post.visibility != VisibilityEnum.PUBLIC:
        if not current_user.is_authenticated:
            abort(403)
        if post.visibility == VisibilityEnum.PRIVATE and post.author != current_user:
            abort(403)
        if post.visibility == VisibilityEnum.FRIENDS and post.author.id not in current_user.friend_ids():
            abort(403)

    # Create comment form if user is authenticated
    form = CommentForm() if current_user.is_authenticated else None

    # If it's an AJAX request, return just the post content template
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('main/_post_content.html', post=post, form=form)

    # For regular requests, return the full page
    is_share = hasattr(post, 'original_post')
    return render_template('main/view_post.html', post=post, form=form, is_share=is_share)

@bp.route('/share/<int:share_id>/like', methods=['POST'])
@login_required
def like_share(share_id):
    share = Share.query.get_or_404(share_id)

    # Check if user already liked this share
    existing_like = Like.query.filter_by(user_id=current_user.id, share_id=share_id).first()

    if existing_like:
        # Unlike
        db.session.delete(existing_like)
        message = 'Share unliked!'
    else:
        # Like
        like = Like(user_id=current_user.id, share_id=share_id)
        db.session.add(like)
        message = 'Share liked!'

    try:
        db.session.commit()
        flash(message, 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error liking/unliking share: {e}")
        flash('Error processing like.', 'danger')

    return redirect(request.referrer or url_for('main.dashboard'))

@bp.route('/share/<int:share_id>/comment', methods=['POST'])
@login_required
def add_comment_to_share(share_id):
    share = Share.query.get_or_404(share_id)
    comment_text = request.form.get('comment_text')

    if not comment_text:
        flash('Comment cannot be empty.', 'danger')
        return redirect(request.referrer or url_for('main.dashboard'))

    comment = Comment(
        content=comment_text,
        user_id=current_user.id,
        share_id=share_id
    )

    try:
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding comment to share: {e}")
        flash('Error adding comment.', 'danger')

    return redirect(request.referrer or url_for('main.dashboard'))

@bp.route('/recommendations')
@login_required
def recommendations():
    friend_recommendations = current_user.get_friend_recommendations(limit=10)
    popular_posts = current_user.get_popular_posts(limit=10)
    
    return render_template('main/recommendations.html',
                         friend_recommendations=friend_recommendations,
                         popular_posts=popular_posts)

@bp.route('/api/friend-recommendations')
@login_required
def get_friend_recommendations():
    recommendations = current_user.get_friend_recommendations(limit=5)
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'profile_pic': user.profile_pic if user.profile_pic else 'images/default.jpg'
    } for user in recommendations])

@bp.route('/api/notifications')
@login_required
def get_notifications():
    try:
        # Log the current user for debugging
        current_app.logger.info(f"Fetching notifications for user {current_user.id}")
        
        # Check if the user exists
        if not current_user:
            current_app.logger.error("No authenticated user found")
            return jsonify({'error': 'User not authenticated'}), 401
            
        # Check database connection
        try:
            db.session.execute(text('SELECT 1'))
        except Exception as db_conn_error:
            current_app.logger.error(f"Database connection error: {str(db_conn_error)}")
            return jsonify({'error': 'Database connection error'}), 500
            
        # Query notifications with error checking
        try:
            notifications = Notification.query.filter_by(user_id=current_user.id)\
                .order_by(Notification.timestamp.desc())\
                .limit(50)\
                .all()
            current_app.logger.info(f"Found {len(notifications)} notifications")
            
            # Convert to dict with error checking
            notifications_data = []
            for notification in notifications:
                try:
                    notifications_data.append(notification.to_dict())
                except Exception as notif_error:
                    current_app.logger.error(f"Error processing notification {notification.id}: {str(notif_error)}")
                    continue  # Skip problematic notifications
                    
            return jsonify(notifications_data)
            
        except Exception as db_error:
            current_app.logger.error(f"Database query error: {str(db_error)}")
            return jsonify({'error': 'Error querying notifications'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_notifications: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@bp.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    try:
        # Log the request for debugging
        current_app.logger.info(f"Marking notification {notification_id} as read for user {current_user.id}")
        
        # Validate notification exists and belongs to user
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=current_user.id
        ).first()
        
        if not notification:
            current_app.logger.warning(f"Notification {notification_id} not found or unauthorized")
            return jsonify({'error': 'Notification not found or unauthorized'}), 404
        
        # Update read status
        try:
            notification.is_read = True
            db.session.commit()
            current_app.logger.info(f"Successfully marked notification {notification_id} as read")
            return jsonify(notification.to_dict())
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"Database error marking notification as read: {str(db_error)}")
            return jsonify({'error': 'Failed to update notification status'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500