from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class EventForm(FlaskForm):
    title = StringField('Title', validators=[
        DataRequired(),
        Length(min=3, max=100, message='Title must be between 3 and 100 characters')
    ])
    
    description = TextAreaField('Description', validators=[
        DataRequired(),
        Length(min=10, max=1000, message='Description must be between 10 and 1000 characters')
    ])
    
    location = StringField('Location', validators=[
        Optional(),
        Length(max=200, message='Location must be less than 200 characters')
    ])
    
    event_datetime = DateTimeField('Date and Time', validators=[
        DataRequired()
    ], format='%Y-%m-%dT%H:%M')
    
    max_participants = IntegerField('Maximum Participants', validators=[
        Optional(),
        NumberRange(min=1, message='Maximum participants must be at least 1')
    ]) 