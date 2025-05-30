from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from ..models import VisibilityEnum # Adjust path to your VisibilityEnum

class PostForm(FlaskForm):
    content = TextAreaField('What\'s on your mind?',
                            validators=[DataRequired(), Length(min=1, max=10000)])
    visibility = SelectField('Visibility',
                             choices=[(choice.value, choice.name.capitalize()) for choice in VisibilityEnum],
                             validators=[DataRequired()])
    submit = SubmitField('Post')