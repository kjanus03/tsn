from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from ..models import Event, EventRSVP, User
from ..extensions import db
from datetime import datetime
from .forms import EventForm
import os
from ..sms import send_rsvp_notification

events_bp = Blueprint('event', __name__)

@events_bp.route('/event')
@login_required
def index():
    # Get upcoming events
    upcoming_events = Event.query.filter(
        Event.event_datetime > datetime.utcnow()
    ).order_by(Event.event_datetime).all()
    
    # Get past events
    past_events = Event.query.filter(
        Event.event_datetime <= datetime.utcnow()
    ).order_by(Event.event_datetime.desc()).all()
    
    return render_template('events/index.html',
                           upcoming_events=upcoming_events,
                           past_events=past_events)

@events_bp.route('/events/create', methods=['GET', 'POST'])
@login_required
def create():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            event_datetime=form.event_datetime.data,
            max_participants=form.max_participants.data,
            creator_id=current_user.id
        )
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('event.view', event_id=event.id))
    return render_template('events/create.html', form=form)

@events_bp.route('/events/<int:event_id>')
@login_required
def view(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('events/view.html', event=event)

@events_bp.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(event_id):
    event = Event.query.get_or_404(event_id)
    if not event.can_edit(current_user):
        flash('You do not have permission to edit this event.', 'danger')
        return redirect(url_for('event.view', event_id=event.id))
    
    form = EventForm(obj=event)
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.location = form.location.data
        event.event_datetime = form.event_datetime.data
        event.max_participants = form.max_participants.data
        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('event.view', event_id=event.id))
    return render_template('events/edit.html', form=form, event=event)

@events_bp.route('/events/<int:event_id>/rsvp', methods=['POST'])
@login_required
def rsvp(event_id):
    event = Event.query.get_or_404(event_id)
    success, message = event.add_rsvp(current_user)
    if success:
        flash('You have RSVP\'d to this event!', 'success')
        # Send SMS notification to event creator
        send_rsvp_notification(event, current_user)
    else:
        flash(message, 'warning')
    return redirect(url_for('event.view', event_id=event.id))

@events_bp.route('/events/<int:event_id>/unrsvp', methods=['POST'])
@login_required
def unrsvp(event_id):
    event = Event.query.get_or_404(event_id)
    if event.remove_rsvp(current_user):
        flash('You have removed your RSVP.', 'success')
    else:
        flash('You were not RSVP\'d to this event.', 'warning')
    return redirect(url_for('event.view', event_id=event.id))

@events_bp.route('/events/<int:event_id>/add-collaborator/<int:user_id>', methods=['POST'])
@login_required
def add_collaborator(event_id, user_id):
    event = Event.query.get_or_404(event_id)
    if not event.can_edit(current_user):
        flash('You do not have permission to add collaborators.', 'danger')
        return redirect(url_for('event.view', event_id=event.id))
    
    user = User.query.get_or_404(user_id)
    if event.add_collaborator(user):
        flash(f'{user.username} has been added as a collaborator.', 'success')
    else:
        flash(f'{user.username} is already a collaborator.', 'warning')
    return redirect(url_for('event.view', event_id=event.id))

@events_bp.route('/events/<int:event_id>/remove-collaborator/<int:user_id>', methods=['POST'])
@login_required
def remove_collaborator(event_id, user_id):
    event = Event.query.get_or_404(event_id)
    if not event.can_edit(current_user):
        flash('You do not have permission to remove collaborators.', 'danger')
        return redirect(url_for('event.view', event_id=event.id))
    
    user = User.query.get_or_404(user_id)
    if event.remove_collaborator(user):
        flash(f'{user.username} has been removed as a collaborator.', 'success')
    else:
        flash(f'{user.username} is not a collaborator.', 'warning')
    return redirect(url_for('event.view', event_id=event.id)) 