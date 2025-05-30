# tsn_app/main/routes.py
import secrets
import uuid
from datetime import datetime, date
import os

from sqlalchemy import or_
from flask_dance.consumer import oauth_authorized, oauth_error
from flask_dance.contrib.google import google  # The proxy for the current Google session
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
# from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_security.utils import hash_password  # Or other utils
from dateutil.parser import parse as parse_date

from .forms import PostForm
from ..models import Post, VisibilityEnum, Like, User, GenderEnum
from .. import db, security

bp = Blueprint('main', __name__,
               template_folder='templates',
               static_folder='static')


@bp.route('/')
def index():
    return render_template('main/index.html')


@bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    post_form = PostForm()  # Instantiate the form for creating new posts

    if post_form.validate_on_submit():  # This checks if it's a POST request and valid
        new_post = Post(
            content=post_form.content.data,
            visibility=VisibilityEnum(post_form.visibility.data),
            user_id=current_user,
            author=current_user
        )
        db.session.add(new_post)
        db.session.commit()
        flash('Your post has been published!', 'success')
        return redirect(url_for('main.dashboard'))

    # get posts
    posts = Post.query.filter(
        (Post.visibility == VisibilityEnum.PUBLIC) |
        ((Post.visibility == VisibilityEnum.FRIENDS) & (Post.user_id.in_(current_user.friend_ids()))) |
        ((Post.visibility == VisibilityEnum.PRIVATE) & (Post.user_id == current_user.id))
    ).order_by(Post.timestamp.desc()).all()

    return render_template('main/dashboard.html', posts=posts, post_form=post_form)


# @bp.route('/create_post', methods=['GET', 'POST'])
# @login_required
# def create_post():
#     if request.method == 'POST':
#         content = request.form['content']
#         visibility = request.form['visibility']
#         post = Post(
#             user_id=current_user.id,
#             content=content,
#             visibility=VisibilityEnum(visibility)
#         )
#         db.session.add(post)
#         db.session.commit()
#         return redirect(url_for('main.dashboard'))
#
#     return render_template('main/create_post.html')


@bp.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    if existing_like:
        db.session.delete(existing_like)
    else:
        like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(like)

    db.session.commit()
    return redirect(request.referrer or url_for('main.dashboard'))


@bp.route('/users')
@login_required
def users():
    page = request.args.get('page', 1, type=int)  # For pagination later
    search_query = request.args.get('q', '').strip()  # Get search query, default to empty string

    query = User.query.filter(User.id != current_user.id)  # Exclude current user

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

# You need to make sure these signal handlers are connected when the tsn_app is created.
# If this code is in tsn_app/__init__.py, it should be fine.
# If it's in a separate file (e.g., tsn_app/oauth_handlers.py), import that file in tsn_app/__init__.py
# so the @oauth_authorized.connect decorator runs.
