# tsn_app/auth/forms.py (or tsn_app/profile/forms.py)
from flask_wtf import FlaskForm # Base form
from flask_wtf.file import FileField, FileAllowed # For file uploads
from wtforms import StringField, DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Email, ValidationError
from ..models import User # needed for custom validation, e.g., unique phone
from ..models import GenderEnum # Assuming GenderEnum is in tsn_app/enums.py
from flask_login import current_user # To pre-fill or validate against current user

# Helper for allowed image extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

class EditProfileForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()],
                        render_kw={'readonly': True})  # Make email read-only
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=64)],
                           render_kw={'readonly': True}) # Make username read-only
    first_name = StringField('First Name',
                             validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name',
                            validators=[DataRequired(), Length(max=64)])
    phone = StringField('Phone Number',
                        validators=[DataRequired(), Length(min=7, max=20)])
    date_birth = DateField('Date of Birth',
                           format='%Y-%m-%d',
                           validators=[DataRequired()])
    gender = SelectField('Gender',
                         choices=[(choice.value, choice.name.replace('_', ' ').title()) for choice in GenderEnum],
                         validators=[DataRequired()])
    profile_pic_upload = FileField('Update Profile Picture',
                                   validators=[FileAllowed(ALLOWED_EXTENSIONS, 'Images only!')]) # FileAllowed validator
    biography = TextAreaField('About Me', validators=[Optional(), Length(max=500)])
    location = TextAreaField('Location', validators=[Optional(), Length(max=100)])

    submit = SubmitField('Update Profile')

    def validate_phone(self, phone):
        if phone.data != current_user.phone: # Only check if the phone number has changed
            user = User.query.filter_by(phone=phone.data).first()
            if user:
                raise ValidationError('That phone number is already in use. Please choose a different one.')

    # Note: If username or email were editable, you'd add similar custom validators
    # to check for uniqueness excluding the current user.
    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')