from flask import Blueprint, render_template, session, redirect, url_for

main_bp = Blueprint('main', __name__)


def redirect_logged_in_user():
    """Redirect logged-in users to their correct dashboard."""

    if not session.get('user_id'):
        return None

    role = session.get('role')

    if role == 'admin':
        return redirect(url_for('admin.dashboard'))

    elif role == 'clinician':
        return redirect(url_for('clinician.dashboard'))

    elif role == 'patient':
        return redirect(url_for('patient.dashboard'))

    # Invalid/stale session
    session.clear()
    return None


@main_bp.route('/')
def index():
    """Public home page."""

    dashboard_redirect = redirect_logged_in_user()

    if dashboard_redirect:
        return dashboard_redirect

    return render_template('index.html')


@main_bp.route('/home')
def home():
    """Home page alias."""

    dashboard_redirect = redirect_logged_in_user()

    if dashboard_redirect:
        return dashboard_redirect

    return render_template('index.html')
