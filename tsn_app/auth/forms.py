# tsn_app/forms.py
from flask_security.forms import RegisterForm, StringField,BooleanField, PasswordField # Import base fields
from wtforms import DateField, SelectField # For Date and Enum
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, Optional
from ..models import GenderEnum # Assuming GenderEnum is in models.py


class ExtendedRegisterForm(RegisterForm): # Inherit from flask_security's RegisterForm
    username = StringField(
        'Username',
        validators=[DataRequired(message="Username is required."), Length(min=3, max=64)]
    )
    first_name = StringField( # Matches 'firstname' in your model if you kept that, or 'first_name' if you changed it
        'First Name',
        validators=[DataRequired(message="First name is required."), Length(max=64)]
    )
    last_name = StringField( # Matches 'lastname' in your model
        'Last Name',
        validators=[DataRequired(message="Last name is required."), Length(max=64)]
    )
    email = StringField( # Overriding to ensure it's here if not in base, or to add specific validators
        'Email',
        validators=[DataRequired(message="Email is required."), Email(), Length(max=255)]
    )
    phone = StringField(
        'Phone Number',
        validators=[
            DataRequired(message="Phone number is required."),
            Length(min=7, max=20), # Adjust length as needed
            Regexp(r'^\+?1?\d{9,15}$', message="Invalid phone number format.")
        ]
    )
    date_birth = DateField( # Matches 'date_birth' in your model
        'Date of Birth',
        format='%Y-%m-%d', # Important for DateField to parse input
        validators=[DataRequired(message="Date of birth is required.")]
    )
    gender = SelectField( # Matches 'gender' in your model
        'Gender',
        choices=[(choice.value, choice.name.replace('_', ' ').title()) for choice in GenderEnum], # Populate choices from Enum
        validators=[DataRequired(message="Gender is required.")]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(message="Password is required."), Length(min=8, message="Password must be at least 8 characters.")]
    )
    password_confirm = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo('password', message='Passwords must match.')
        ]
    )
    # Flask-Security's RegisterForm might handle 'submit' already.
    # If not, or if you want to customize:
    # from wtforms import SubmitField
    # submit = SubmitField('Register')

    # Note: 'profile_pic' is usually handled by a separate profile edit form after registration,
    # as file uploads on a registration form can be complex.
    # 'active' and 'fs_uniquifier' are typically handled by Flask-Security internally, not form fields.