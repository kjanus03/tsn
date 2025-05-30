from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required


bp = Blueprint('connections', __name__, template_folder='templates')

@bp.route('/connections')
@login_required
def connections():
    # Query the graph to list current connections of the user
    connections = []  # For now, an empty list or hardcoded sample data
    return render_template('connections/list.html', connections=connections)

@bp.route('/connections/add', methods=['POST'])
@login_required
def add_connection():
    new_friend_username = request.form.get('username')
    # Lookup user and update your connection table/graph structure
    flash(f"Connection request sent to {new_friend_username}", "success")
    return redirect(url_for('connections.connections'))
